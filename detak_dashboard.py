# dashboard.py
import os
from dotenv import load_dotenv
from flask import Flask, render_template
from pymongo import MongoClient
from datetime import datetime, timedelta
from pytz import timezone, UTC

# Load environment variables
load_dotenv()

# MongoDB Configuration
MONGO_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("MONGODB_DB")
COLLECTION_NAME = os.getenv("MONGODB_COLLECTION")
OBJECTS_COLLECTION = os.getenv("MONGODB_OBJECTS_COLLECTION")

app = Flask(__name__)

# Define a custom Jinja2 filter for datetime formatting
@app.template_filter('datetimeformat')
def datetimeformat(value, format='%Y-%m-%d %H:%M:%S'):
    try:
        # Parse the UTC timestamp
        utc_time = datetime.fromisoformat(value).replace(tzinfo=UTC)
        # Convert to UTC+7
        utc_plus_7 = utc_time.astimezone(timezone('Asia/Jakarta'))
        return utc_plus_7.strftime(format)
    except ValueError:
        return value

def get_status_data():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    main_collection = db[COLLECTION_NAME]
    objects_collection = db[OBJECTS_COLLECTION]

    # Get timestamps for 1 hour ago and 24 hours ago
    one_hour_ago = datetime.now() - timedelta(hours=1)
    twenty_four_hours_ago = datetime.now() - timedelta(hours=24)

    # Aggregate data by UUID, limiting to the last 24 hours
    pipeline = [
        {"$match": {"timestamp": {"$gte": twenty_four_hours_ago.isoformat()}}},  # Only fetch data from the last 24 hours
        {"$sort": {"timestamp": 1}},  # Sort by timestamp in ascending order
        {"$group": {
            "_id": "$uuid",
            "timestamps": {"$push": "$timestamp"},  # Collect all timestamps
            "lastHeartbeat": {"$last": "$timestamp"},
            "totalPings": {"$sum": 1}
        }}
    ]

    results = list(main_collection.aggregate(pipeline))

    # Fetch object_name for each UUID from the objects collection
    for item in results:
        object_data = objects_collection.find_one({"uuid": item["_id"]})  # Ensure UUID is used
        item["objectName"] = object_data["object_name"] if object_data else "Unknown Object"

        # Calculate minuteStatuses for the last 1 hour
        timestamps = [datetime.fromisoformat(ts).replace(tzinfo=UTC) for ts in item["timestamps"]]
        timestamps = [ts for ts in timestamps if ts >= one_hour_ago]
        minute_statuses = []
        current_time = one_hour_ago

        for ts in timestamps:
            # Fill inactive (red) for missing minutes
            while current_time < ts:
                minute_statuses.append("inactive")
                current_time += timedelta(minutes=1)

            # Add active (green) for the current timestamp
            minute_statuses.append("active")
            current_time += timedelta(minutes=1)

        # Fill remaining inactive (red) minutes up to the current time
        while current_time <= datetime.now():
            minute_statuses.append("inactive")
            current_time += timedelta(minutes=1)

        # Limit to the last 60 minutes
        item["minuteStatuses"] = minute_statuses[-60:]

        # Calculate total pings in the last 24 hours
        total_pings_24h = len([ts for ts in item["timestamps"] if datetime.fromisoformat(ts) >= twenty_four_hours_ago])

        # Calculate 24-hour uptime percentage
        item['uptime'] = round((total_pings_24h / 1440) * 100, 2)  # 1440 = 24 hours in minutes

    client.close()

    # Calculate status
    for item in results:
        try:
            item['status'] = 'active' if (
                datetime.now() - datetime.fromisoformat(item['lastHeartbeat'])
            ).seconds < 120 else 'inactive'
        except ValueError:
            item['status'] = 'inactive'

    return sorted(results, key=lambda x: x['status'], reverse=True)

@app.route('/')
def dashboard():
    status_data = get_status_data()
    return render_template('dashboard.html', services=status_data)

if __name__ == '__main__':
    app.run(debug=True)