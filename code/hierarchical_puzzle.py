"""
EXPERIMENT 8 - AGENTS COLLABORATING TO SOLVE DISTRIBUTED PUZZLE SOLVING
ARCHITECTURE : HIERARCHICAL (MASTER - WORKER)

Puzzle  : N-Queens (place N queens on an N x N board so that no two
          queens attack each other). Each COLUMN of the board is owned
          by one WORKER AGENT, which is only responsible for deciding
          the ROW of its own queen.

Design  :
    MasterAgent (coordinator, single point of authority)
        |----> WorkerAgent_0 (column 0)
        |----> WorkerAgent_1 (column 1)
        |----> ...
        |----> WorkerAgent_{N-1}

    * Workers NEVER talk to each other directly.
    * Every decision flows UP to the Master (worker -> master) and every
      update flows DOWN from the Master (master -> worker) - a strict
      top-down chain of command, which is the defining trait of a
      Hierarchical multi-agent architecture.
"""

import queue
import threading
import random
import time

N = 8                       # board size / number of queens / number of agents
MAX_ROUNDS = 200            # safety limit so the demo always terminates


# --------------------------------------------------------------------------
# Helper: conflict counter
# --------------------------------------------------------------------------
def conflicts_for(board, col, row):
    """Number of queens that attack the queen placed at (col, row)."""
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
# WORKER AGENT  -  owns exactly one column / one queen
# --------------------------------------------------------------------------
class WorkerAgent(threading.Thread):
    def __init__(self, col, inbox, master_inbox):
        super().__init__(daemon=True)
        self.col = col
        self.inbox = inbox              # messages coming DOWN from master
        self.master_inbox = master_inbox  # messages going UP to master

    def run(self):
        while True:
            msg = self.inbox.get()
            if msg["type"] == "STOP":
                break

            if msg["type"] == "REQUEST_PROPOSAL":
                board = msg["board"]
                # Local reasoning: try every row in my own column and
                # report the row with the fewest conflicts (min-conflicts),
                # breaking ties randomly so the swarm does not oscillate.
                best_conf = conflicts_for(board, self.col, board[self.col])
                best_rows = [board[self.col]]
                for row in range(N):
                    c = conflicts_for(board, self.col, row)
                    if c < best_conf:
                        best_conf, best_rows = c, [row]
                    elif c == best_conf and row not in best_rows:
                        best_rows.append(row)
                best_row = random.choice(best_rows)

                self.master_inbox.put({
                    "type": "PROPOSAL",
                    "col": self.col,
                    "row": best_row,
                    "conflicts": best_conf
                })


# --------------------------------------------------------------------------
# MASTER AGENT  -  the single coordinator / decision-maker
# --------------------------------------------------------------------------
class MasterAgent:
    def __init__(self, n):
        self.n = n
        self.board = [random.randint(0, n - 1) for _ in range(n)]
        self.master_inbox = queue.Queue()
        self.workers = []
        self.worker_inboxes = []

        for col in range(n):
            inbox = queue.Queue()
            worker = WorkerAgent(col, inbox, self.master_inbox)
            self.worker_inboxes.append(inbox)
            self.workers.append(worker)
            worker.start()

    def broadcast_board(self):
        """Master -> every worker: 'here is the board, propose your move'."""
        for inbox in self.worker_inboxes:
            inbox.put({"type": "REQUEST_PROPOSAL", "board": list(self.board)})

    def collect_and_apply(self):
        """
        Collect one proposal from every worker, then the master applies the
        single best proposal (centralised conflict resolution). This is
        what keeps authority hierarchical: workers propose, master decides.
        """
        proposals = [self.master_inbox.get() for _ in range(self.n)]
        best_conf = min(p["conflicts"] for p in proposals)
        candidates = [p for p in proposals if p["conflicts"] == best_conf]
        best = random.choice(candidates)          # randomised tie-break
        self.board[best["col"]] = best["row"]
        return best

    def run(self):
        print(f"[MASTER] Initial board (random)  : {self.board}")
        print(f"[MASTER] Initial total conflicts  : {total_conflicts(self.board)}\n")

        stagnant_rounds = 0
        prev_conf = total_conflicts(self.board)

        for round_no in range(1, MAX_ROUNDS + 1):
            self.broadcast_board()
            applied = self.collect_and_apply()
            conf = total_conflicts(self.board)
            print(f"Round {round_no:3d} | Master applied Worker-{applied['col']} "
                  f"-> row {applied['row']} | total conflicts = {conf}")

            # Plateau detection: if stuck at the same conflict count for too
            # long, the master issues a top-down "random kick" - it forces a
            # randomly chosen worker's column to a fresh random row. This
            # is a hierarchical escape from local minima (only the master
            # can order this, workers cannot do it on their own).
            if conf == prev_conf:
                stagnant_rounds += 1
            else:
                stagnant_rounds = 0
            prev_conf = conf

            if stagnant_rounds >= 15 and conf != 0:
                kick_col = random.randrange(self.n)
                self.board[kick_col] = random.randrange(self.n)
                print(f"           ...plateau detected -> Master forces "
                      f"Worker-{kick_col} to a random row {self.board[kick_col]}")
                stagnant_rounds = 0

            if conf == 0:
                print(f"\n[MASTER] Solution found in {round_no} rounds!")
                print(f"[MASTER] Final board (row per column) : {self.board}")
                self.print_board()
                self.shutdown()
                return

        print("\n[MASTER] Max rounds reached without a perfect solution.")
        self.shutdown()

    def print_board(self):
        for r in range(self.n):
            line = ""
            for c in range(self.n):
                line += " Q " if self.board[c] == r else " . "
            print(line)

    def shutdown(self):
        for inbox in self.worker_inboxes:
            inbox.put({"type": "STOP"})


if __name__ == "__main__":
    print("=" * 70)
    print(" HIERARCHICAL ARCHITECTURE - DISTRIBUTED N-QUEENS PUZZLE SOLVING")
    print("=" * 70)
    master = MasterAgent(N)
    master.run()
