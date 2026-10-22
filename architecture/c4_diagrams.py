"""Generate mcl-turn-credentials' two C4 diagrams into assets/.

Run:  python3 architecture/c4_diagrams.py

  c4-context.svg     Level 1: what the service talks to
  c4-components.svg  Level 2: what it is made of

Drawn from the code, never from a template: the callbacks in
mcl_turn_credentials_service.erl, the RPC provider in
mint_turn_credential.erl, the dependencies in rebar.config, the port and volumes in
the Containerfile and deploy/docker-compose.yml. When one of those changes, the
diagram changes in the same commit.

Colours are plain classes with a prefers-color-scheme: dark block, no CSS custom
properties (rsvg-convert renders those black), so the SVGs render the same on
GitHub, in IDE previews and through rsvg-convert. After a change, render each
(rsvg-convert -w 1400 assets/c4-context.svg -o /tmp/c.png) and look at it; keep
architecture/README.md's tables in step.
"""
import os
from xml.sax.saxutils import escape

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")

SANS = '"Atkinson Hyperlegible", "Segoe UI", system-ui, -apple-system, Helvetica, Arial, sans-serif'
MONO = '"JetBrains Mono", ui-monospace, Menlo, Consolas, monospace'

# Element kinds, each (light fill, light stroke, dark fill, dark stroke).
KINDS = {
    "b-sys": ("#F5E9CC", "#A56F0A", "#3A2E13", "#E3AA3C"),   # in scope
    "b-per": ("#E3EBF2", "#3B5B7A", "#1D2A36", "#8EB4D8"),   # person
    "b-mac": ("#E6E4EE", "#5E5A78", "#26243A", "#A9A4C8"),   # Macula infrastructure
    "b-ext": ("#ECEFED", "#8A9791", "#1C2421", "#7D8B85"),   # external system
    "b-cmp": ("#FFFFFF", "#8A9791", "#171F1C", "#7D8B85"),   # component or container
}

STYLE = f"""<style>
.t-name {{ font-family: {SANS}; font-size: 15px; font-weight: 700; }}
.t-desc {{ font-family: {SANS}; font-size: 12.5px; }}
.t-rel {{ font-family: {SANS}; font-size: 11.5px; paint-order: stroke; stroke-width: 4px; stroke-linejoin: round; }}
.t-code {{ font-family: {MONO}; font-size: 13px; font-weight: 600; }}
.t-type {{ font-family: {MONO}; font-size: 11.5px; }}
.t-bound {{ font-family: {MONO}; font-size: 12px; font-weight: 600; }}
.t-leg {{ font-family: {SANS}; font-size: 12px; }}
.edge {{ fill: none; stroke-width: 1.25; }}
.edge-later {{ fill: none; stroke-width: 1.25; stroke-dasharray: 5 4; }}
.bg {{ fill: #FFFFFF; }}
""" + "".join(f".{k} {{ fill: {v[0]}; stroke: {v[1]}; stroke-width: {2 if k == 'b-sys' else 1.25}; }}\n" for k, v in KINDS.items()) + """\
.b-later { fill: none; stroke: #8A9791; stroke-width: 1.25; stroke-dasharray: 5 4; }
.bound { fill: none; stroke: #B3BDB8; stroke-width: 1; }
.head { fill: #3B5B7A; }
.t-name, .t-code { fill: #16201D; }
.t-type, .t-bound, .t-leg { fill: #66736E; }
.t-desc { fill: #34413C; }
.t-rel { fill: #66736E; stroke: #FFFFFF; }
.edge, .edge-later { stroke: #8A9791; }
.arrowhead { fill: #8A9791; }
@media (prefers-color-scheme: dark) {
.bg { fill: #171F1C; }
""" + "".join(f".{k} {{ fill: {v[2]}; stroke: {v[3]}; }}\n" for k, v in KINDS.items()) + """\
.b-later { stroke: #7D8B85; }
.bound { stroke: #4A5752; }
.head { fill: #8EB4D8; }
.t-name, .t-code { fill: #E6ECE9; }
.t-type, .t-bound, .t-leg { fill: #93A09A; }
.t-desc { fill: #C3CDC8; }
.t-rel { fill: #93A09A; stroke: #171F1C; }
.edge, .edge-later { stroke: #7D8B85; }
.arrowhead { fill: #7D8B85; }
}
</style>"""

DEFS = ('<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
        'orient="auto-start-reverse"><path class="arrowhead" d="M0 0L10 5L0 10z"/></marker></defs>')

LEGEND = [("b-sys", "In scope"), ("b-per", "Person"), ("b-mac", "Macula infrastructure"),
          ("b-ext", "External system"), ("b-cmp", "Container or component")]
BOUNDARY = ("bound", "Boundary")


class Diagram:
    def __init__(self, name, title, w, h):
        self.name, self.title, self.w, self.h, self.parts = name, title, w, h, []

    def text(self, cls, x, y, s, anchor=None, rotate=None):
        a = f' text-anchor="{anchor}"' if anchor else ""
        r = f' transform="rotate({rotate} {x} {y})"' if rotate is not None else ""
        self.parts.append(f'<text class="{cls}" x="{x}" y="{y}"{a}{r}>{escape(s)}</text>')

    def box(self, cls, x, y, w, h, name, kind, desc, person=False, code=False):
        # A box that is too small for its own words renders as text on top of the
        # next box, which no test would catch and a reader would read as the
        # diagram saying something it does not. Fail here instead.
        need = 70 + 16 * max(len(desc) - 1, 0) + 18
        if h < need:
            raise ValueError(f"{self.name}: {name} needs height {need}, has {h}")
        for line in desc:
            if 16 + 6.2 * len(line) > w - 16:
                raise ValueError(f"{self.name}: {name}: '{line}' is wider than {w - 32}px")
        self.parts.append(f'<rect class="{cls}" x="{x}" y="{y}" width="{w}" height="{h}" rx="10"/>')
        tx = x + 16
        if person:
            self.parts.append(f'<circle class="head" cx="{x + 26}" cy="{y + 24}" r="9"/>')
            tx = x + 44
        self.text("t-code" if code else "t-name", tx, y + 28, name)
        self.text("t-type", tx, y + 46, kind)
        for i, line in enumerate(desc):
            self.text("t-desc", x + 16, y + 70 + 16 * i, line)

    def bound(self, x, y, w, h, label):
        self.parts.append(f'<rect class="bound" x="{x}" y="{y}" width="{w}" height="{h}" rx="12"/>')
        self.text("t-bound", x + 16, y + 22, label)

    def edge(self, d, later=False):
        self.parts.append(f'<path class="{"edge-later" if later else "edge"}" d="{d}" marker-end="url(#a)"/>')

    def legend(self, y, boundary=True):
        x = 24
        for cls, label in LEGEND + ([BOUNDARY] if boundary else []):
            self.parts.append(f'<rect class="{cls}" x="{x}" y="{y}" width="22" height="14" rx="3"/>')
            self.text("t-leg", x + 30, y + 12, label)
            x += 34 + 6.6 * len(label)

    def write(self):
        svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" role="img" '
               f'aria-label="{escape(self.title)}">', f"<title>{escape(self.title)}</title>", STYLE, DEFS,
               f'<rect class="bg" x="0" y="0" width="{self.w}" height="{self.h}"/>'] + self.parts + ["</svg>", ""]
        with open(os.path.join(OUT, self.name), "w") as f:
            f.write("\n".join(svg))


def context():
    d = Diagram("c4-context.svg", "mcl-turn-credentials system context", 1000, 680)
    d.box("b-per", 40, 30, 270, 120, "Caller", "[Person]",
          ["A client app, or the ICE agent", "inside it, that needs a TURN", "allocation"], person=True)
    d.box("b-per", 690, 30, 270, 104, "Service operator", "[Person]",
          ["Deploys the release and supplies", "TURN_SHARED_SECRET from the host"], person=True)
    d.box("b-sys", 365, 186, 270, 138, "mcl-turn-credentials", "[mcl_om mesh service, own box]",
          ["Serves its own procedure,", "mcl-turn-credentials/mint_credential,", "and /health on 8485. Holds the",
           "secret; never places a call"])
    d.box("b-ext", 40, 392, 270, 120, "coturn TURN server", "[External system]",
          ["Derives the same username and", "password from the same secret at", "ALLOCATE, so nothing is sent to it"])
    d.box("b-mac", 365, 392, 270, 120, "macula-realm", "[Macula infrastructure]",
          ["Endorses the node's identity key", "and grants the scope it asks for,", "mcl-turn-credentials"])
    d.box("b-mac", 690, 392, 270, 120, "Macula stations, mesh DHT", "[Macula infrastructure]",
          ["The pinned stations are its mesh", "entry points (QUIC); the mesh DHT", "takes the endpoint it announces"])
    d.edge("M175 150V168H400V186")
    d.text("t-rel", 183, 160, "calls mint_credential,"); d.text("t-rel", 183, 176, "and is answered")
    d.edge("M825 134V168H620V186")
    d.text("t-rel", 690, 160, "deploys; sets TURN_SHARED_SECRET")
    d.edge("M420 324V392"); d.text("t-rel", 428, 352, "boot claim, scope")
    d.edge("M620 324V360H825V392"); d.text("t-rel", 632, 352, "announces its endpoint, re-announced periodically")
    d.edge("M40 80H20V456H40")
    d.text("t-rel", 24, 268, "ALLOCATE with the minted pair", anchor="middle", rotate=-90)
    d.text("t-desc", 40, 566, "The service never calls coturn: both sides derive the same pair from TURN_SHARED_SECRET, so the")
    d.text("t-desc", 40, 584, "master secret stays on the box instead of shipping inside every client app.")
    d.legend(630, boundary=False)
    d.write()


def components():
    d = Diagram("c4-components.svg", "mcl-turn-credentials components", 1000, 810)
    d.bound(16, 40, 968, 510, "mcl-turn-credentials [Container]")
    d.box("b-cmp", 32, 70, 456, 120, "mcl_turn_credentials_service", "[mcl_om_service behaviour]",
          ["The mcl_om_service callbacks: start, stop, health,", "capabilities, identity_spec. capabilities/0 declares",
           "mint_credential; mcl_om adds info and get_limits"], code=True)
    d.box("b-cmp", 512, 70, 456, 120, "mcl_turn_credentials_sup", "[supervisor, one_for_one]",
          ["Supervises this service's own processes.", "No children: the RPC provider is started",
           "when mcl_om registers capabilities"], code=True)
    d.box("b-sys", 32, 214, 456, 140, "mint_turn_credential", "[macula_response RPC provider]",
          ["handle_request/2 mints one credential per call:", "username is a unix expiry, password is",
           "base64(HMAC-SHA1(secret, username)). TTL 1 h,", "one TURN URL. Every reply string is tagged text"], code=True)
    d.box("b-cmp", 512, 214, 456, 120, "health/0", "[the mcl_om_service health callback]",
          ["down while TURN_SHARED_SECRET is unset or empty,", "because every mint would fail. A dark mesh is",
           "deliberately NOT a health failure here"], code=True)
    d.box("b-mac", 32, 374, 456, 152, "mcl_om", "[library, ~> 1.4]",
          ["boot/1: loads the node identity key, joins the", "realm, opens the QUIC pool through the pinned",
           "stations, and registers what capabilities/0", "returns; answers info and get_limits, both open;",
           "serves /health on MCL_HEALTH_PORT"], code=True)
    d.box("b-mac", 512, 374, 456, 120, "macula SDK", "[library, ~> 16.0, wire 1.0]",
          ["QUIC transport, RPC dispatch to a provider that", "answers by name, and the signed records the mesh",
           "DHT holds"], code=True)
    d.box("b-ext", 40, 574, 920, 88, "TURN_SHARED_SECRET", "[environment, from the host; the container does not hold it]",
          ["coturn's static-auth-secret, byte for byte; deploy/docker-compose.yml refuses to start without it"], code=True)
    d.edge("M488 132H512"); d.text("t-rel", 500, 124, "starts", anchor="middle")
    d.edge("M200 190V214"); d.text("t-rel", 208, 206, "declares in capabilities/0")
    d.edge("M260 354V374"); d.text("t-rel", 268, 370, "runs inside")
    d.edge("M488 344H520V374"); d.text("t-rel", 528, 366, "replies through")
    d.edge("M488 470H500V358H700V334")
    d.text("t-rel", 704, 348, "calls health/0 on every probe")
    d.edge("M32 284H20V618H40")
    d.text("t-rel", 22, 470, "reads at every call", anchor="middle", rotate=-90)
    d.edge("M488 444H512"); d.text("t-rel", 504, 436, "puts, serves", anchor="end")
    d.text("t-desc", 40, 700, "config/sys.config.src fixes the org, mcl-turn-credentials, which prefixes its own procedure's name; it also")
    d.text("t-desc", 40, 718, "pins the realm key, so an unpinned or unendorsed boot is refused rather than")
    d.text("t-desc", 40, 736, "left looking healthy. deploy/docker-compose.yml mounts one named volume, /etc/mcl/secrets, for the node key.")
    d.legend(770)
    d.write()


if __name__ == "__main__":
    for make in (context, components):
        make()
