%% @doc The mcl_om service contract: what this service is and may do.
%%
%% SIX CALLBACKS, ALL REQUIRED. mcl_om resolves them BY NAME at startup, on a
%% live node, so a service that forgets one dies with `undef' where nobody is
%% watching. The `-behaviour' attribute below is what turns that into a compile
%% error instead, and the generated test suite guards the attribute itself.
-module(mcl_turn_credentials_service).

-behaviour(mcl_om_service).

-export([info/0, start/1, stop/1, health/0, capabilities/0, identity_spec/0]).

info() ->
    #{name => <<"mcl-turn-credentials">>,
      version => <<"0.1.0">>,
      description => <<"Mints short-lived TURN credentials over the mesh, keeping the master secret out of client apps">>}.

start(_Opts) -> mcl_turn_credentials_sup:start_link().

stop(_State) -> ok.

%% The one thing this service needs to do its job at all: without
%% TURN_SHARED_SECRET every mint call fails, so a missing secret is a real
%% health failure. Set-but-empty is the same failure, see mint_turn_credential.
%% A dark mesh is NOT a health failure here, deliberately.
health() -> health(os:getenv("TURN_SHARED_SECRET")).

health(false) -> {down, turn_shared_secret_not_configured};
health("") -> {down, turn_shared_secret_not_configured};
health(Secret) when is_list(Secret) -> ok.

%% WHAT THIS SERVICE ANNOUNCES IT CAN DO. Declaring `handler' makes
%% mcl_om_capabilities register the procedure with the pool and publish its
%% signed direct-dial record at boot, re-advertised periodically. On the wire
%% the name is `mcl-turn-credentials/mint_credential': the org comes from
%% sys.config.
%%
%% `auth => open' is a decision, not a default: any peer that reaches the
%% procedure gets a credential, because the service exists to keep the master
%% secret out of public clients, not to decide who may place a call.
capabilities() ->
    [#{name => <<"mint_credential">>,
       version => 1,
       handler => {mint_turn_credential, []},
       auth => open}].

%% THE AUTHORITY THIS SERVICE ASKS THE REALM FOR, and deliberately nothing more.
%% Ask for exactly the topics you publish and subscribe to. Popped, an attacker
%% gains precisely this and no more, which is the whole point of listing it.
%%
%% The scope is claimed now because it is the namespace every later resource
%% hangs under, and a scope costs nothing while a rename costs every deployed
%% peer.
identity_spec() ->
    #{scope => <<"mcl-turn-credentials">>,
      actions => [],
      resources => [],
      ttl_days => 30}.
