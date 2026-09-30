"""
EXPERIMENT 8 - AGENTS COLLABORATING TO SOLVE DISTRIBUTED PUZZLE SOLVING
ARCHITECTURE : PEER-TO-PEER (FULLY DECENTRALIZED, NO COORDINATOR AT ALL)

Puzzle  : N-Queens, one queen (column) per agent - same puzzle as the
          other two architectures, so the three can be compared fairly.

Design  :
    There is NO master and NO zone coordinator of any kind. Every
    QueenAgent is a fully autonomous PEER. Each agent has its own inbox
    (mailbox) and is directly connected to every OTHER agent's inbox.
    An agent that changes its own row BROADCASTS that change directly
    to all peers - this is classic "gossip" / Asynchronous Backtracking
    style communication used in Distributed CSP algorithms.

        Q0 <-----> Q1 <-----> Q2 <-----> ... <-----> Q(N-1)
         \_______________ fully-connected mesh ______________/

    Every agent independently decides, from its own local view of the
    board, whether to move - there is no single entity anyone reports to.
"""

import queue
import threading
import random
import time

N = 8                      # board size / number of queens / number of agents
MAX_ROUNDS = 300           # safety limit
STOP_EVENT = threading.Event()
BOARD_LOCK = threading.Lock()


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


def print_board(board, n):
    for r in range(n):
        line = ""
        for c in range(n):
            line += " Q " if board[c] == r else " . "
        print(line)


# --------------------------------------------------------------------------
# QUEEN AGENT - fully autonomous PEER, no coordinator above it
# --------------------------------------------------------------------------
class QueenAgent(threading.Thread):
    def __init__(self, col, shared_board, event_log, agent_id_to_thread):
        super().__init__(daemon=True)
        self.col = col
        self.shared_board = shared_board       # the ONE shared blackboard
        self.inbox = queue.Queue()             # mailbox other peers post to
        self.event_log = event_log
        self.peers = []                        # filled in after all agents exist
        self.rounds_done = 0

    def set_peers(self, peers):
        self.peers = peers

    def broadcast_move(self, new_row):
        """Directly notify every other peer agent of my move (no middle-man)."""
        for peer in self.peers:
            peer.inbox.put({"from": self.col, "row": new_row})

    def drain_inbox(self):
        """Peers just use this to know activity happened; the authoritative
        state is the shared board itself (protected by BOARD_LOCK), mirroring
        how P2P networks reconcile a shared ledger/blackboard."""
        while not self.inbox.empty():
            self.inbox.get()

    def run(self):
        rng = random.Random(self.col * 7919 + 13)  # per-agent random stream
        while not STOP_EVENT.is_set() and self.rounds_done < MAX_ROUNDS:
            self.drain_inbox()

            with BOARD_LOCK:
                board_snapshot = list(self.shared_board)

            my_row = board_snapshot[self.col]
            my_conf = conflicts_for(board_snapshot, self.col, my_row)

            if my_conf > 0:
                # Min-conflicts move, decided completely locally by this agent
                best_conf = my_conf
                best_rows = [my_row]
                for row in range(N):
                    c = conflicts_for(board_snapshot, self.col, row)
                    if c < best_conf:
                        best_conf, best_rows = c, [row]
                    elif c == best_conf and row not in best_rows:
                        best_rows.append(row)

                # Occasional random walk step to escape local minima -
                # a purely local decision, no global authority involved.
                if rng.random() < 0.1:
                    new_row = rng.randrange(N)
                else:
                    new_row = rng.choice(best_rows)

                if new_row != my_row:
                    with BOARD_LOCK:
                        self.shared_board[self.col] = new_row
                    self.broadcast_move(new_row)
                    self.event_log.append((self.col, new_row))

            self.rounds_done += 1
            time.sleep(0.001)   # tiny yield so all threads interleave fairly


if __name__ == "__main__":
    print("=" * 70)
    print(" PEER-TO-PEER ARCHITECTURE - DISTRIBUTED N-QUEENS PUZZLE SOLVING")
    print("=" * 70)

    board = [random.randint(0, N - 1) for _ in range(N)]
    print(f"[SYSTEM] Initial board          : {board}")
    print(f"[SYSTEM] Initial total conflicts : {total_conflicts(board)}\n")

    event_log = []
    agents = [QueenAgent(c, board, event_log, None) for c in range(N)]
    for agent in agents:
        agent.set_peers([a for a in agents if a is not agent])
        agent.start()

    last_printed_conf = None
    solved = False
    check_interval = 0.05

    for tick in range(1, 4000):
        time.sleep(check_interval)
        with BOARD_LOCK:
            conf = total_conflicts(board)
            snapshot = list(board)

        if conf != last_printed_conf:
            print(f"Tick {tick:4d} | some peer(s) moved | board = {snapshot} "
                  f"| total conflicts = {conf}")
            last_printed_conf = conf

        if conf == 0:
            solved = True
            break

        if all(a.rounds_done >= MAX_ROUNDS for a in agents):
            break

    STOP_EVENT.set()
    time.sleep(0.05)

    if solved:
        print(f"\n[SYSTEM] All peer agents converged to a conflict-free board!")
        print(f"[SYSTEM] Final board (row per column): {board}")
        print_board(board, N)
    else:
        print("\n[SYSTEM] Peers did not fully converge within the tick budget "
              f"(final conflicts = {total_conflicts(board)}). "
              "Re-run, or raise MAX_ROUNDS / tick budget.")
