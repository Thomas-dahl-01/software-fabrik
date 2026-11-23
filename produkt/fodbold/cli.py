"""Kommandolinje: læser argumenter og printer resultater."""

import argparse

from fodbold import db, spillere


def byg_parser():
    parser = argparse.ArgumentParser(
        prog="fodbold", description="Football Team Manager"
    )
    omraader = parser.add_subparsers(dest="omraade", required=True)

    spiller = omraader.add_parser("spiller", help="Opret og vis spillere")
    handlinger = spiller.add_subparsers(dest="handling", required=True)

    opret = handlinger.add_parser("opret", help="Opret en ny spiller")
    opret.add_argument("--navn", required=True, help="Spillerens navn")
    opret.add_argument(
        "--nummer", required=True, type=int, help="Trøjenummer (heltal)"
    )
    opret.add_argument("--position", required=True, help="Spillerens position")

    handlinger.add_parser("liste", help="Vis alle spillere på holdet")
    return parser


def formater_spillere(liste):
    """Lav en tekstoversigt over spillerne."""
    if not liste:
        return "Ingen spillere på holdet."
    linjer = [f"{'Nr.':>4}  {'Navn':<25} Position"]
    for s in liste:
        linjer.append(f"{s['troejenummer']:>4}  {s['navn']:<25} {s['position']}")
    return "\n".join(linjer)


def main(argv=None, forbindelse=None):
    args = byg_parser().parse_args(argv)
    if forbindelse is None:
        forbindelse = db.forbind()

    if args.omraade == "spiller":
        if args.handling == "opret":
            spillere.opret_spiller(forbindelse, args.navn, args.nummer, args.position)
            print(f"Oprettede spiller nr. {args.nummer}: {args.navn} ({args.position})")
        elif args.handling == "liste":
            print(formater_spillere(spillere.hent_spillere(forbindelse)))
    return 0
