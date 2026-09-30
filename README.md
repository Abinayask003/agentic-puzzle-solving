# Distributed Puzzle Solving with Multi-Agent Architectures

**Course:** Agentic AI — Experiment 8
**Puzzle:** N-Queens (8×8), solved by agents that each own one queen/column
**Goal:** Implement and compare three multi-agent coordination architectures —
Hierarchical, Decentralized, and Peer-to-Peer — solving the *same* puzzle.

## Live demos (GitHub Pages)

| Architecture | Demo |
|---|---|
| Hierarchical | `web/hierarchical.html` |
| Decentralized | `web/decentralized.html` |
| Peer-to-Peer | `web/peer_to_peer.html` |

Once GitHub Pages is enabled for this repo (see below), these will be reachable at:

```
https://<your-username>.github.io/agentic-puzzle-solving/web/hierarchical.html
https://<your-username>.github.io/agentic-puzzle-solving/web/decentralized.html
https://<your-username>.github.io/agentic-puzzle-solving/web/peer_to_peer.html
```

## Repository structure

```
agentic-puzzle-solving/
├── README.md
├── code/
│   ├── hierarchical_puzzle.py      # Master–Worker architecture
│   ├── decentralized_puzzle.py     # Zone-coordinator architecture
│   └── peer_to_peer_puzzle.py      # Fully autonomous mesh architecture
└── web/
    ├── hierarchical.html           # Live browser visualization
    ├── decentralized.html
    └── peer_to_peer.html
```

## Running the Python scripts

No external dependencies — standard library only (`queue`, `threading`, `random`, `time`).

```bash
python3 code/hierarchical_puzzle.py
python3 code/decentralized_puzzle.py
python3 code/peer_to_peer_puzzle.py
```

## Running the web visualizations

Each `.html` file is fully self-contained — no build step, no server required.
Just open the file directly in a browser, or use VS Code's Live Server extension.

## Architecture summary

- **Hierarchical** — one Master agent holds the board and makes every decision;
  Worker agents (one per queen) can only *propose* moves.
- **Decentralized** — the board is split into zones, each with its own
  coordinator; coordinators gossip with each other as peers, with no single
  global authority.
- **Peer-to-Peer** — no coordinator at all; every queen agent is directly
  connected to every other agent and decides its own moves autonomously.

All three converge to a valid, conflict-free board — demonstrating that the
same problem can be solved through structurally different coordination
strategies.
