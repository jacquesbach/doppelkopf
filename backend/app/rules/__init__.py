"""Regelkern fuer Doppelkopf nach DDV-Turnierspielregeln (TSR, Stand 21.02.2026).

Reines Python, ohne Flask, Datenbank, Socket.IO oder Zeitbezug. Siehe ``docs/DDV_REGELMATRIX.md``.
"""
from .announcements import AnnouncementBook, allowed_levels, check_announcement
from .cards import Card, DeckVariant, Rank, Suit, build_deck, card, hand_size
from .dealing import deal, shuffled_deck
from .errors import DuplicateAction, RuleViolation, VersionConflict
from .game import (Announce, Baptize, Declare, GameKind, GameState, Phase, PlayCard, Resolve,
                   DeclareSchweinchen, PovertyOffer, PovertyPass, PovertyReturn, apply_action, bot_view,
                   can_declare_poverty, can_declare_schweinchen, legal_actions, new_game, player_view,
                   spectator_view)
from .parties import Party
from .options import OPTION_SPECS, RuleOptions, normalize_settings, rule_schema, settings_from_dict
from .profile import (RuleProfile, RuleProfileId, ddv_profile, house_no_nines_profile, make_profile,
                      profile_from_settings, validate_combination)
from .round_rules import (RoundState, is_round_finished, new_round, next_setup, record_game,
                          start_next_game)
from .scoring import GameScore, score_game
from .tricks import CompletedTrick, Play, playable_cards, trick_winner_index
from .trump import SOLO_TYPES, GameType, TrumpConfig, is_trump, suit_order, trump_count, trump_order

__all__ = [name for name in dir() if not name.startswith("_")]
