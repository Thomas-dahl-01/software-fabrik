"""Kommandolinje: læser argumenter og printer resultater."""

import argparse

from fodbold import db, kampe, spillere


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

    kamp = omraader.add_parser("kamp", help="Registrér og vis kampe")
    kamp_handlinger = kamp.add_subparsers(dest="handling", required=True)

    registrer = kamp_handlinger.add_parser("registrer", help="Registrér en kamp")
    registrer.add_argument(
        "--dato", required=True, help="Kampens dato i ISO-format (ÅÅÅÅ-MM-DD)"
    )
    registrer.add_argument("--modstander", required=True, help="Modstanderens navn")
    registrer.add_argument(
        "--spillested",
        required=True,
        choices=kampe.SPILLESTEDER,
        help="Hjemme- eller udekamp",
    )
    registrer.add_argument("--resultat", required=True, help="Resultat, fx 2-1")

    kamp_handlinger.add_parser("liste", help="Vis alle kampe")
    return parser


def formater_spillere(liste):
    """Lav en tekstoversigt over spillerne."""
    if not liste:
        return "Ingen spillere på holdet."
    linjer = [f"{'Nr.':>4}  {'Navn':<25} Position"]
    for s in liste:
        linjer.append(f"{s['troejenummer']:>4}  {s['navn']:<25} {s['position']}")
    return "\n".join(linjer)


def formater_kampe(liste):
    """Lav en tekstoversigt over kampene."""
    if not liste:
        return "Ingen kampe registreret."
    linjer = [f"{'Dato':<10}  {'Modstander':<25} {'Sted':<6} Resultat"]
    for k in liste:
        linjer.append(
            f"{k['dato']:<10}  {k['modstander']:<25} {k['spillested']:<6} {k['resultat']}"
        )
    return "\n".join(linjer)


def vis_kampe(forbindelse):
    """Udskriv en liste over alle kampe i terminalen."""
    print(formater_kampe(kampe.hent_kampe(forbindelse)))


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
    elif args.omraade == "kamp":
        if args.handling == "registrer":
            try:
                kampe.registrer_kamp(
                    forbindelse,
                    args.dato,
                    args.modstander,
                    args.spillested,
                    args.resultat,
                )
            except ValueError as fejl:
                print(f"Fejl: {fejl}")
                return 1
            print(
                f"Registrerede kamp {args.dato}: {args.modstander} "
                f"({args.spillested}) {args.resultat}"
            )
        elif args.handling == "liste":
            vis_kampe(forbindelse)
    return 0
