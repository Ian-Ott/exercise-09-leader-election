"""
TODO: Implement the Bully algorithm for leader election.

Functions to implement:
- start_election(): initiate an election, send ELECTION messages to higher-ID nodes
- handle_election_message(sender_id): respond to election from lower-ID node
- declare_victory(): announce self as leader to all nodes
- heartbeat_check(): periodically check if leader is alive
"""

# TODO: Implement the Bully algorithm
import threading
import time
import requests
import logging
import os

logger = logging.getLogger(__name__)

# Variables globales
leader_id = None
election_in_progress = False

# Intervalos
HEARTBEAT_INTERVAL = 5
HEARTBEAT_TIMEOUT = 3

# Variables de entorno esperadas:
# NODE_ID
# PEERS = "http://node-2:8080,http://node-3:8080"

NODE_ID = int(os.getenv("NODE_ID", "1"))
PEERS = os.getenv("PEERS", "").split(",")


def get_peer_id(peer_url: str) -> int:
    """
    Extrae el ID desde el hostname.
    Ejemplo:
    http://node-2:8080 -> 2
    """
    try:
        hostname = peer_url.split("//")[1].split(":")[0]
        return int(hostname.split("-")[1])
    except Exception:
        return -1


def start_election():
    """
    Inicia elección Bully:
    - Envía ELECTION a nodos con ID mayor.
    - Si nadie responde, se declara líder.
    """
    global election_in_progress

    if election_in_progress:
        return

    election_in_progress = True

    logger.info(f"[Node {NODE_ID}] Starting election")

    higher_nodes = [
        peer for peer in PEERS
        if get_peer_id(peer) > NODE_ID
    ]

    received_ok = False

    for peer in higher_nodes:
        try:
            response = requests.post(
                f"{peer}/election",
                json={"sender_id": NODE_ID},
                timeout=2
            )

            if response.status_code == 200:
                received_ok = True

        except Exception as e:
            logger.warning(f"Election message failed to {peer}: {e}")

    if not received_ok:
        declare_victory()
    else:
        logger.info(f"[Node {NODE_ID}] Higher node exists")


def handle_election_message(sender_id: int):
    """
    Un nodo menor inició elección.
    Responder OK y comenzar elección propia.
    """
    logger.info(
        f"[Node {NODE_ID}] Received election from Node {sender_id}"
    )

    if sender_id < NODE_ID:
        threading.Thread(target=start_election, daemon=True).start()

    return {
        "status": "OK",
        "node_id": NODE_ID
    }


def declare_victory():
    """
    Se declara líder y notifica a todos los nodos.
    """
    global leader_id
    global election_in_progress

    leader_id = NODE_ID
    election_in_progress = False

    logger.info(f"[Node {NODE_ID}] Declaring victory")

    for peer in PEERS:
        try:
            requests.post(
                f"{peer}/coordinator",
                json={"leader_id": NODE_ID},
                timeout=2
            )

        except Exception as e:
            logger.warning(f"Coordinator message failed to {peer}: {e}")


def set_leader(new_leader_id: int):
    """
    Actualiza líder actual.
    """
    global leader_id
    global election_in_progress

    leader_id = new_leader_id
    election_in_progress = False

    logger.info(f"[Node {NODE_ID}] New leader is Node {leader_id}")


def heartbeat_check():
    """
    Verifica periódicamente si el líder sigue vivo.
    Si no responde, inicia elección.
    """
    global leader_id

    while True:
        time.sleep(HEARTBEAT_INTERVAL)

        if leader_id is None:
            start_election()
            continue

        if leader_id == NODE_ID:
            continue

        leader_url = None

        for peer in PEERS:
            if get_peer_id(peer) == leader_id:
                leader_url = peer
                break

        if not leader_url:
            start_election()
            continue

        try:
            response = requests.get(
                f"{leader_url}/health",
                timeout=HEARTBEAT_TIMEOUT
            )

            if response.status_code != 200:
                raise Exception("Leader unhealthy")

        except Exception:
            logger.warning(
                f"[Node {NODE_ID}] Leader {leader_id} unreachable"
            )

            leader_id = None
            start_election()