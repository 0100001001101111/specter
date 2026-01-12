"""SPECTER Configuration"""
import os

# Supabase Configuration
SUPABASE_URL = "https://diwkdydpjakvwmzyijrk.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRpd2tkeWRwamFrdndtenlpanJrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njc0OTc2NTgsImV4cCI6MjA4MzA3MzY1OH0.UjmFGml5rGhWMSSqignGr5WseyjRl_MMCZrMIuxG_dY"

# Target Area: Portland, OR Metro
PORTLAND_BBOX = {
    'min_lat': 45.2,
    'max_lat': 45.7,
    'min_lon': -123.2,
    'max_lon': -122.2
}

OREGON_BBOX = {
    'min_lat': 41.99,
    'max_lat': 46.29,
    'min_lon': -124.57,
    'max_lon': -116.46
}

# Portland metro center
PORTLAND_CENTER = (45.5152, -122.6784)
PORTLAND_RADIUS_KM = 50

# Data directories
BASE_DIR = os.path.expanduser("~/specter")
DATA_DIR = os.path.join(BASE_DIR, "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
CACHE_DIR = os.path.join(DATA_DIR, "cache")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
LOG_DIR = os.path.join(BASE_DIR, "logs")

# Rate limiting
NOMINATIM_DELAY = 1.1  # seconds between requests
NUFORC_DELAY = 0.5
OVERPASS_DELAY = 1.0

# Analysis parameters
CLUSTER_EPS_METERS = 500
CLUSTER_MIN_SAMPLES = 5
PERMUTATION_ITERATIONS = 100  # Reduced for speed
