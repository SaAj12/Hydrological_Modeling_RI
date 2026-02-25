"""
Fetch GPM IMERG precipitation data for a bounding box.
Data source: GPM_3IMERGDF.07 (daily, 0.1 deg).
Requires: Earthdata Login + .netrc, and pip install harmony-py xarray s3fs (or earthaccess).
Run from project root (D:\\Brown\\SWAT\\viewer3) or D:\\go\\pr.
"""
# Region (your box)
NORTH = 42.350747
SOUTH = 41.095955
WEST = -72.245582
EAST = -70.711999

# Example: one day
import datetime as dt

def get_precipitation_for_region(start_date: dt.date, end_date: dt.date):
    """Use Harmony to subset GPM IMERG by this region and date range."""
    try:
        from harmony import BBox, Client, Collection, Request, LinkType
        import xarray as xr
    except ImportError:
        print("Install: pip install harmony-py xarray s3fs")
        return None
    # GPM IMERG Final Daily at GES DISC (check Harmony for exact collection id)
    request = Request(
        collection=Collection(id="C1940473810-GES_DISC"),  # verify at harmony.earthdata.nasa.gov
        spatial=BBox(WEST, SOUTH, EAST, NORTH),
        temporal={"start": dt.datetime.combine(start_date, dt.time.min),
                  "stop": dt.datetime.combine(end_date, dt.time.max)},
    )
    client = Client()
    job_id = client.submit(request)
    client.wait_for_processing(job_id)
    results = client.result_urls(job_id, link_type=LinkType.http)
    return list(results)

if __name__ == "__main__":
    start = dt.date(2020, 1, 1)
    end = dt.date(2020, 1, 7)
    urls = get_precipitation_for_region(start, end)
    if urls:
        print("Result URLs:", urls)
