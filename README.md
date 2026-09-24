# mcl-turn-credentials

**Mints short-lived TURN credentials over the mesh, keeping the master secret out of client apps**

Built on macula 12 and `mcl_om`.

## What it does

It serves one procedure, **`mcl-turn-credentials/mint_credential`**, and
answers `/health` on 8485.

A call returns one TURN credential in coturn's use-auth-secret (REST API)
scheme: the username is a unix expiry timestamp and the password is
`base64(HMAC-SHA1(secret, username))`. coturn derives the same pair from the
same secret when the client allocates, so the service never talks to coturn,
and the master secret never ships inside a client app.

    #{username    => {text, <<"1790000000">>},
      credential  => {text, <<"base64 HMAC">>},
      ttl_seconds => 3600,
      urls        => [{text, <<"turn:turn.macula.io:3478?transport=udp">>}]}

Every string in the reply is tagged text. A bare binary would reach non-BEAM
callers as 0x-hex, and a hex username is useless to an ICE agent.

The procedure is **open**: any peer that reaches it gets a credential. The
service keeps the secret out of public clients; it does not decide who may
place a call. It asks the realm for no pubsub authority, because it publishes
and subscribes to nothing.

`/health` is `down` while `TURN_SHARED_SECRET` is unset or empty, because
every mint call would fail. A dark mesh is not a health failure.

## Running it

    rebar3 compile
    rebar3 eunit
    rebar3 lint
    rebar3 dialyzer

    scripts/health.sh                      # against a running node

Building the image needs a Rust toolchain, because macula ships a QUIC NIF and
the alpine build compiles it from source rather than fetching one linked against
a different libc.

    podman build -t mcl-turn-credentials -f Containerfile .

## Configuration

| Variable | Default | Meaning |
|----------|---------|---------|
| `MCL_REALM` | required | 64-hex realm tag, the `sha256` of the realm's name. No default: a service that guesses its realm announces itself where nobody can attribute it. |
| `MCL_REALM_KEY` | required | The realm's public signing key, hex encoded: the **trust anchor**, not an identifier. Every org-namespaced advertisement is verified against it, so without it nothing resolves, the boot claim never reaches the realm, and the service stays green while unreachable. Public material, not a secret. |
| `MACULA_STATION_SEEDS` | required | Station hosts to dial, `host[:port]`, comma-separated. No default: naming a realm costs nothing, dialling a production station from every dev clone does. |
| `MACULA_STATION_NODE_IDS` | required | The matching 64-hex station node ids, comma-separated, index-paired with the seeds. The dial is pinned (D5): mcl_om refuses to boot a pool with an unpinned seed. |
| `TURN_SHARED_SECRET` | required | coturn's `static-auth-secret`, byte for byte. A secret: supply it from the host, never commit it. Without it `/health` is `down` and every call answers `turn_shared_secret_not_configured`. |
| `MCL_SERVICE_NAME` | `mcl-turn-credentials` | The service label on the claim the realm's operator sees at boot. Falls back to the service's own name. |
| `MCL_BOX` | empty | The host label on that claim: which box is asking. Set by whatever deploys the service. |
| `MCL_HEALTH_PORT` | `8485` | Health endpoint, assigned in macula-fleet `PORTS.md`. Host networking makes a collision a silent bind failure, so take a new one from there rather than picking one. |
| `MCL_NODE_NAME` | `mcl_turn_credentials` | Erlang node name. |
| `MCL_NODE_HOST` | `127.0.0.1` | Erlang node host. |
| `MCL_COOKIE` | `mcl_turn_credentials` | Erlang cookie. |

`deploy/docker-compose.yml` runs it, and carries what the service knows about
itself. If you deploy through something else, let that carry **placement**: which
host, which station, which realm, which secret store. Keeping the two apart is
what stops a config table in a README and the real environment drifting.

## Deployment

The image has two channels. A push to `main` publishes
`ghcr.io/macula-services/mcl-turn-credentials:latest`, the deploy channel: a host that follows
`:latest` deploys every merge. A `v*` tag publishes its own version and nothing
else, the rollback archive: pin a host to one to roll back. A push that changes
only documentation builds no image (`scripts/is_image_push.sh`).

The service's org, the `<org>` in every procedure it offers (`<org>/<name>`), is
this repository's name, fixed in `config/sys.config.src`. The realm's grant names
it; without an org mcl_om advertises nothing.

Two things CI cannot do for you, both of which have bitten:

1. The registry package may be created **private**, and the pull then fails on
   the host with a bare `unauthorized` that names nothing. Check it after the
   first build. On ghcr the `org.opencontainers.image.source` label in the
   Containerfile is what links the package to the repository.
2. The host needs `MCL_REALM`, the pinned station pair and
   `TURN_SHARED_SECRET` supplied from somewhere they are not committed.

## The service contract

Six callbacks in `mcl_turn_credentials_service`, all required, all resolved **by name** by
`mcl_om` at startup on a live node. The `-behaviour(mcl_om_service)`
attribute turns a missing one into a compile error rather than an `undef` where
nobody is watching, and the eunit suite guards the attribute itself.

### Adding a store later

This service has no `reckon-db` store, which is the right answer for most. The
reckon-db applications run either way; what a store adds is a data directory, an
open handle, and something written.

The cheapest way to get one is to scaffold again with `store=1`, which generates
the callbacks, the config and the guards together.

⚠ **By hand it is three things and not one, and the missing third crash-loops the
node.** Export `store_id/0` and `data_dir/0`; add the `evoq` adapter block to
`config/sys.config.src`, without which boot raises
`{not_configured, event_store_adapter}` before any service code runs; and mount a
volume in the compose file. A sibling service put two of three fleet nodes into a
boot loop by doing the first and not the second.

## Licence

Apache-2.0.
