%% @doc RPC provider: `mcl-turn-credentials/mint_credential'. Mints one
%% short-lived TURN credential from a master secret that lives only in this
%% process's environment, never in a client app. Follows coturn's
%% use-auth-secret / REST-API convention exactly: username is a unix expiry
%% timestamp, password is base64(HMAC-SHA1(secret, username)). coturn derives
%% the same pair independently from the same secret at ALLOCATE time, so
%% nothing round-trips to coturn here.
%%
%% No input is required or checked. Every mesh peer that can reach this
%% procedure gets a credential: this exists to keep the master secret out of a
%% public client, not to gate who may place a call. Contact and call
%% authorization is a separate concern, owned by the calling app.
%%
%% EVERY STRING IN THE REPLY IS `{text, Bin}'. A bare binary encodes as a CBOR
%% byte string, which every non-BEAM caller renders as 0x-hex, and an ICE agent
%% cannot send a hex-rendered username to coturn.
-module(mint_turn_credential).

-behaviour(macula_response).

-export([init/1, handle_request/2]).

%% Covers one call session without mid-call credential rotation. coturn's own
%% relay-allocation lifetime (refreshed by the ICE agent) is independent of
%% this; the TTL only bounds how long the USERNAME/PASSWORD pair is accepted
%% for a fresh ALLOCATE.
-define(TTL_SECONDS, 3600).

%% One deployed TURN server. Worth a config knob only once a second exists.
-define(TURN_URL, <<"turn:turn.macula.io:3478?transport=udp">>).

init(_Args) -> {ok, undefined}.

handle_request(_Payload, State) ->
    mint(os:getenv("TURN_SHARED_SECRET"), State).

%% Unset and set-but-empty are the same failure: HMAC over an empty key still
%% yields a password, one coturn rejects at ALLOCATE.
mint(false, State) ->
    {error, turn_shared_secret_not_configured, State};
mint("", State) ->
    {error, turn_shared_secret_not_configured, State};
mint(Secret, State) when is_list(Secret) ->
    {reply, credential(list_to_binary(Secret)), State}.

credential(Secret) ->
    Expiry = erlang:system_time(second) + ?TTL_SECONDS,
    Username = integer_to_binary(Expiry),
    Password = base64:encode(crypto:mac(hmac, sha, Secret, Username)),
    #{
        username    => {text, Username},
        credential  => {text, Password},
        ttl_seconds => ?TTL_SECONDS,
        urls        => [{text, ?TURN_URL}]
    }.
