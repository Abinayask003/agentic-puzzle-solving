"""
EXPERIMENT 8 - AGENTS COLLABORATING TO SOLVE DISTRIBUTED PUZZLE SOLVING
ARCHITECTURE : DECENTRALIZED (MULTIPLE COOPERATING COORDINATORS)

Puzzle  : N-Queens, one queen (column) per WorkerAgent, exactly like the
          hierarchical version - but now there is NO single master.

Design  :
    The N columns are split into Z ZONES. Each zone has its own
    ZoneCoordinatorAgent that behaves like a small local "master" for
    the workers inside its zone. Crucially, the coordinators are PEERS
    of each other - they exchange the current board directly, without
    any higher authority above them.

        Zone-0 Coordinator <---> Zone-1 Coordinator <---> Zone-2 Coordinator
              |                        |                        |
          W0 W1 W2 ...             Wk Wk+1 ...                 ...

    This is what makes it "decentralized": control is partitioned into
    several autonomous authorities that must negotiate with each other
    (rather than one global authority, and rather than fully flat P2P).
"""

import queue
import threading
import random

N = 8                     # board size / number of queens
ZONES = 2                 # number of independent zone-coordinators
MAX_GLOBAL_ROUNDS = 150   # rounds of inter-zone negotiation
MAX_LOCAL_ROUNDS = 8      # rounds each zone runs internally per global round


def conflicts_for(board, col, row):
    c = 0
    for other_col, other_row in enumerate(board):
        if other_col == col:
            continue
        if other_row == row or abs(other_row - row) == abs(other_col - col):
            c += 1
    return c


def total_conflicts(board):
    return sum(conflicts_for(board, c, r) for c, r in enumerate(board)) // 2


# --------------------------------------------------------------------------
# WORKER AGENT - identical role to the hierarchical version: owns 1 column
# --------------------------------------------------------------------------
class WorkerAgent(threading.Thread):
    def __init__(self, col, inbox, coordinator_inbox):
        super().__init__(daemon=True)
        self.col = col
        self.inbox = inbox
        self.coordinator_inbox = coordinator_inbox

    def run(self):
        while True:
            msg = self.inbox.get()
            if msg["type"] == "STOP":
                break
            if msg["type"] == "REQUEST_PROPOSAL":
                board = msg["board"]
                best_conf = conflicts_for(board, self.col, board[self.col])
                best_rows = [board[self.col]]
                for row in range(N):
                    c = conflicts_for(board, self.col, row)
                    if c < best_conf:
                        best_conf, best_rows = c, [row]
                    elif c == best_conf and row not in best_rows:
                        best_rows.append(row)
                best_row = random.choice(best_rows)
                self.coordinator_inbox.put({
                    "type": "PROPOSAL", "col": self.col,
                    "row": best_row, "conflicts": best_conf
                })


# --------------------------------------------------------------------------
# ZONE COORDINATOR AGENT - a *local* authority, peer to other coordinators
# --------------------------------------------------------------------------
class ZoneCoordinatorAgent:
    def __init__(self, zone_id, columns, shared_board):
        self.zone_id = zone_id
        self.columns = columns              # list of column indices owned by this zone
        self.shared_board = shared_board    # reference to the GLOBAL board (list)
        self.inbox = queue.Queue()          # messages from peer coordinators
        self.coordinator_inbox = queue.Queue()  # replies from own workers
        self.workers = {}
        self.worker_inboxes = {}
        for col in columns:
            wi = queue.Queue()
            w = WorkerAgent(col, wi, self.coordinator_inbox)
            self.worker_inboxes[col] = wi
            self.workers[col] = w
            w.start()
        self.peers = []   # set later: list of other ZoneCoordinatorAgent

    def set_peers(self, peers):
        self.peers = peers

    def run_local_optimization(self):
        """Optimize only the columns owned by THIS zone, treating other
        zones' queens (visible via shared_board) as fixed background."""
        for _ in range(MAX_LOCAL_ROUNDS):
            for col in self.columns:
                self.worker_inboxes[col].put({
                    "type": "REQUEST_PROPOSAL", "board": list(self.shared_board)
                })
            proposals = [self.coordinator_inbox.get() for _ in self.columns]
            best_conf = min(p["conflicts"] for p in proposals)
            candidates = [p for p in proposals if p["conflicts"] == best_conf]
            best = random.choice(candidates)
            self.shared_board[best["col"]] = best["row"]

    def broadcast_to_peers(self):
        """Peer-to-peer communication AMONG coordinators (no master)."""
        for peer in self.peers:
            peer.inbox.put({
                "type": "ZONE_UPDATE", "from": self.zone_id,
                "board_snapshot": list(self.shared_board)
            })

    def receive_peer_updates(self):
        """Drain messages from peer coordinators; the shared_board list is
        already common state, so this just synchronizes / acknowledges."""
        while not self.inbox.empty():
            self.inbox.get()

    def shutdown(self):
        for wi in self.worker_inboxes.values():
            wi.put({"type": "STOP"})


def print_board(board, n):
    for r in range(n):
        line = ""
        for c in range(n):
            line += " Q " if board[c] == r else " . "
        print(line)


if __name__ == "__main__":
    print("=" * 70)
    print(" DECENTRALIZED ARCHITECTURE - DISTRIBUTED N-QUEENS PUZZLE SOLVING")
    print("=" * 70)

    board = [random.randint(0, N - 1) for _ in range(N)]
    print(f"[SYSTEM] Initial board          : {board}")
    print(f"[SYSTEM] Initial total conflicts : {total_conflicts(board)}\n")

    # Partition columns into zones, e.g. N=8, ZONES=2 -> [0,1,2,3] and [4,5,6,7]
    cols_per_zone = [list(range(N))[i::ZONES] for i in range(ZONES)]
    coordinators = [ZoneCoordinatorAgent(z, cols_per_zone[z], board) for z in range(ZONES)]
    for coord in coordinators:
        coord.set_peers([c for c in coordinators if c is not coord])

    prev_conf = total_conflicts(board)
    stagnant = 0

    for g_round in range(1, MAX_GLOBAL_ROUNDS + 1):
        # Every zone coordinator independently improves its own queens
        for coord in coordinators:
            coord.run_local_optimization()

        # Coordinators then gossip their results to peer coordinators
        for coord in coordinators:
            coord.broadcast_to_peers()
        for coord in coordinators:
            coord.receive_peer_updates()

        conf = total_conflicts(board)
        print(f"Global round {g_round:3d} | zones = {ZONES} | board = {board} "
              f"| total conflicts = {conf}")

        if conf == prev_conf:
            stagnant += 1
        else:
            stagnant = 0
        prev_conf = conf

        if stagnant >= 4 and conf != 0:
            # Decentralized escape: each coordinator independently decides
            # (no global order) to shake up ONE of its own queens.
            for coord in coordinators:
                col = random.choice(coord.columns)
                board[col] = random.randrange(N)
            print("             ...plateau detected -> each zone coordinator "
                  "independently perturbs one of its own queens")
            stagnant = 0

        if conf == 0:
            print(f"\n[SYSTEM] Solution found after {g_round} global rounds!")
            print(f"[SYSTEM] Final board (row per column): {board}")
            print_board(board, N)
            break
    else:
        print("\n[SYSTEM] Max global rounds reached without a perfect solution.")

    for coord in coordinators:
        coord.shutdown()
