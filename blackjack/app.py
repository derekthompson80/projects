from __future__ import annotations

import os
import random
from dataclasses import dataclass
from typing import List, Tuple
from flask import Flask, render_template, redirect, url_for, session, flash

"""
Single-player Blackjack (web) using Flask.

How to run (from project root):
  - python -m projects.blackjack.app
  or
  - python projects\blackjack\app.py

Then open http://127.0.0.1:5000/ in your browser.

Game rules:
- Single player vs. dealer using a standard 52-card deck.
- Dealer hits until total >= 17 (Aces count as 11 where possible without busting).
- Blackjack pays 3:2 (only on initial deal of 2 cards totaling 21).
- Player can Hit or Stand. No splitting/doubling for simplicity.
- Deck is reshuffled when it runs low.
"""

app = Flask(__name__)
app.secret_key = os.environ.get("BLACKJACK_SECRET", "dev-secret-key-change-me")

# ---- Card / Deck helpers ----
SUITS = ["♠", "♥", "♦", "♣"]
RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]

@dataclass(frozen=True)
class Card:
    rank: str
    suit: str

    def __str__(self) -> str:
        return f"{self.rank}{self.suit}"


def build_deck() -> List[Card]:
    return [Card(rank, suit) for suit in SUITS for rank in RANKS]


def shuffle_deck(deck: List[Card]) -> None:
    random.shuffle(deck)


def draw(deck: List[Card]) -> Card:
    if not deck:
        # Auto-reshuffle a fresh deck if we ran out
        deck.extend(build_deck())
        shuffle_deck(deck)
    return deck.pop()


def hand_value(cards: List[Card]) -> Tuple[int, bool]:
    """Return (total, is_soft). A soft hand counts an Ace as 11 without busting."""
    total = 0
    aces = 0
    for c in cards:
        if c.rank == "A":
            aces += 1
            total += 11
        elif c.rank in ("J", "Q", "K"):
            total += 10
        else:
            total += int(c.rank)
    # Reduce Aces from 11 to 1 as needed
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    is_soft = any(c.rank == "A" for c in cards) and total <= 21 and any(
        # If we could reduce by 10 and still be >= 12, it's soft; simpler: if any Ace still counted as 11
        True for _ in []
    )
    # The above trick isn't great; compute properly: soft if there's an Ace counted as 11
    # Recompute quickly
    tmp_total = 0
    tmp_aces = 0
    for c in cards:
        if c.rank == "A":
            tmp_aces += 1
            tmp_total += 11
        elif c.rank in ("J", "Q", "K"):
            tmp_total += 10
        else:
            tmp_total += int(c.rank)
    while tmp_total > 21 and tmp_aces > 0:
        tmp_total -= 10
        tmp_aces -= 1
    is_soft = tmp_aces > 0 and tmp_total <= 21
    return total, is_soft


# ---- Session State helpers ----

def _init_game_state() -> None:
    session["deck"] = [f"{c.rank}|{c.suit}" for c in build_deck()]
    random.shuffle(session["deck"])  # shuffle in place
    session["player"] = []
    session["dealer"] = []
    session["state"] = "idle"  # idle, player, dealer, round_over
    session["message"] = "Welcome to Blackjack! Click Deal to start."
    session.setdefault("bankroll", 1000)


def _load_deck() -> List[Card]:
    deck_ser = session.get("deck", [])
    return [Card(rank=s.split("|")[0], suit=s.split("|")[1]) for s in deck_ser]


def _save_deck(deck: List[Card]) -> None:
    session["deck"] = [f"{c.rank}|{c.suit}" for c in deck]


def _deal_initial() -> None:
    deck = _load_deck()
    player: List[Card] = []
    dealer: List[Card] = []
    for _ in range(2):
        player.append(draw(deck))
        dealer.append(draw(deck))
    _save_deck(deck)
    session["player"] = [f"{c.rank}|{c.suit}" for c in player]
    session["dealer"] = [f"{c.rank}|{c.suit}" for c in dealer]
    total_p, _ = hand_value(player)
    total_d, _ = hand_value(dealer)
    # Check for natural blackjack
    if total_p == 21 and total_d != 21:
        # Blackjack pays 3:2
        session["bankroll"] = session.get("bankroll", 1000) + int(1.5 * 10)  # base bet 10
        session["state"] = "round_over"
        session["message"] = "Blackjack! You win 15 chips."
    elif total_p == 21 and total_d == 21:
        session["state"] = "round_over"
        session["message"] = "Push! Both have Blackjack."
    else:
        session["state"] = "player"
        session["message"] = "Your move: Hit or Stand."


def _get_hands() -> Tuple[List[Card], List[Card]]:
    p = [Card(rank=c[:-1] if c[:-1] != "10" else "10", suit=c[-1]) for c in session.get("player", [])]
    # But since we stored as rank|suit, better parse accordingly
    def parse(serial: str) -> Card:
        rank, suit = serial.split("|")
        return Card(rank, suit)
    player = [parse(s) for s in session.get("player", [])]
    dealer = [parse(s) for s in session.get("dealer", [])]
    return player, dealer


@app.route("/")
def index():
    if "deck" not in session:
        _init_game_state()
    player, dealer = _get_hands()
    total_p, _ = hand_value(player) if player else (0, False)
    # Hide dealer hole card unless round is over or dealer's turn is finished
    state = session.get("state", "idle")
    show_dealer_all = state in ("dealer", "round_over") and len(dealer) > 0
    if not show_dealer_all and dealer:
        visible_dealer = [str(dealer[0])] + ["⍰⍰"] * (len(dealer) - 1)
        total_d = None
    else:
        visible_dealer = [str(c) for c in dealer]
        total_d, _ = hand_value(dealer) if dealer else (0, False)
    msg = session.get("message", "")
    bankroll = session.get("bankroll", 1000)
    return render_template(
        "index.html",
        player_cards=[str(c) for c in player],
        dealer_cards=visible_dealer,
        total_player=total_p,
        total_dealer=total_d,
        state=state,
        message=msg,
        bankroll=bankroll,
    )


@app.route("/deal")
def deal():
    # If round over or idle, (re)deal. If player mid-round, ignore.
    if "deck" not in session:
        _init_game_state()
    state = session.get("state")
    if state in ("idle", "round_over"):
        # Reshuffle if deck running low
        deck = _load_deck()
        if len(deck) < 10:
            deck = build_deck()
            shuffle_deck(deck)
            _save_deck(deck)
        session["player"] = []
        session["dealer"] = []
        _deal_initial()
    return redirect(url_for("index"))


@app.route("/hit")
def hit():
    if session.get("state") != "player":
        return redirect(url_for("index"))
    deck = _load_deck()
    player, dealer = _get_hands()
    player.append(draw(deck))
    _save_deck(deck)
    session["player"] = [f"{c.rank}|{c.suit}" for c in player]
    total_p, _ = hand_value(player)
    if total_p > 21:
        session["state"] = "round_over"
        session["message"] = f"You bust with {total_p}. Dealer wins."
        session["bankroll"] = session.get("bankroll", 1000) - 10
    else:
        session["message"] = "Your move: Hit or Stand."
    return redirect(url_for("index"))


@app.route("/stand")
def stand():
    if session.get("state") != "player":
        return redirect(url_for("index"))
    session["state"] = "dealer"
    deck = _load_deck()
    player, dealer = _get_hands()
    # Dealer hits until 17 or more
    while True:
        total_d, _ = hand_value(dealer)
        if total_d >= 17:
            break
        dealer.append(draw(deck))
    _save_deck(deck)
    session["dealer"] = [f"{c.rank}|{c.suit}" for c in dealer]

    total_p, _ = hand_value(player)
    total_d, _ = hand_value(dealer)
    bankroll = session.get("bankroll", 1000)
    if total_d > 21:
        session["message"] = f"Dealer busts with {total_d}. You win!"
        bankroll += 10
    elif total_p > total_d:
        session["message"] = f"You win {total_p} vs dealer {total_d}!"
        bankroll += 10
    elif total_p < total_d:
        session["message"] = f"Dealer wins {total_d} vs your {total_p}."
        bankroll -= 10
    else:
        session["message"] = f"Push at {total_p}."
    session["bankroll"] = bankroll
    session["state"] = "round_over"
    return redirect(url_for("index"))


@app.route("/new")
def new_round():
    # Shortcut to start next hand
    if session.get("state") == "round_over":
        return redirect(url_for("deal"))
    return redirect(url_for("index"))


@app.route("/reset")
def reset_game():
    _init_game_state()
    flash("Game reset.")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
