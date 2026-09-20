import time

from fund_helpers import (
    asset_to_response,
    get_order,
    get_pending_orders,
    mongo_database,
    remove_order,
)


def pending_orders():
    return get_pending_orders()

if __name__ == "__main__":
    while True:
        i = 0
        for p in pending_orders():
            i += 1
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"{i}: {timestamp} : {p}", flush=True) # flush to see output immediately 
        #print(pending_orders())
        time.sleep(10)