import numpy as np
import faiss

from flask import Flask, request, jsonify

import signal
import json
import time
from threading import Thread

from src.db import first_register_service, register_service, stop_signal_handler
from src.constants import DATA_GENERATION, CLUSTER

cluster_center = np.load(
    f"/var/data/{DATA_GENERATION}/clusters_centers.pkl", allow_pickle=True
)[str(CLUSTER)]
search_index = faiss.read_index(
    f"/var/data/{DATA_GENERATION}/{CLUSTER}/search_index.faiss"
)
with open(f"/var/data/{DATA_GENERATION}/{CLUSTER}/idx_to_doc.json") as f:
    idx_to_doc = json.load(f)


def redis_heartbeat():
    cluster_center_str = ",".join([str(v) for v in cluster_center])
    while True:
        time.sleep(30)
        register_service(cluster_center_str)


app = Flask(__name__)


@app.route("/get_k_neighbours", methods=["POST"])
def get_k_neighbours():
    k = int(request.args.get("k"))
    vector = request.json.get("embedding")

    _, I = search_index.search(vector, k)
    return jsonify(documents=[idx_to_doc[i] for i in I.tolist()])


if __name__ == "__main__":
    # before stopping, remove the data about the service from redis
    signal.signal(signal.SIGINT, stop_signal_handler)
    signal.signal(signal.SIGTERM, stop_signal_handler)

    # register for the first time, set expiration
    first_register_service(",".join([str(v) for v in cluster_center]))

    # start background heartbeat
    thread = Thread(target=redis_heartbeat)
    thread.start()

    # start the app
    app.run(host="0.0.0.0", port=5000)
