-module(mint_turn_credential_tests).

-include_lib("eunit/include/eunit.hrl").

-define(SECRET_ENV, "TURN_SHARED_SECRET").

no_secret_configured_fails_test() ->
    os:unsetenv(?SECRET_ENV),
    Result = mint_turn_credential:handle_request(#{}, undefined),
    ?assertEqual({error, turn_shared_secret_not_configured, undefined}, Result).

%% An exported-but-empty variable is not a secret. HMAC over an empty key still
%% produces a password, one coturn rejects at ALLOCATE, so the caller would get
%% a credential that looks fine and never works.
empty_secret_is_not_a_secret_test() ->
    os:putenv(?SECRET_ENV, ""),
    Result = mint_turn_credential:handle_request(#{}, undefined),
    os:unsetenv(?SECRET_ENV),
    ?assertEqual({error, turn_shared_secret_not_configured, undefined}, Result).

%% Verifies the actual HMAC scheme, not just the reply's shape: coturn derives
%% password = base64(HMAC-SHA1(secret, username)) independently at ALLOCATE
%% time, so a credential this module mints has to satisfy that same formula
%% against the username it hands back, or coturn rejects it.
mints_a_credential_matching_the_hmac_scheme_test() ->
    #{username := {text, Username}, credential := {text, Credential},
      ttl_seconds := Ttl, urls := Urls} = mint("test-secret"),
    Expected = base64:encode(crypto:mac(hmac, sha, <<"test-secret">>, Username)),
    ?assertEqual(Expected, Credential),
    ?assertEqual(3600, Ttl),
    ?assertEqual([{text, <<"turn:turn.macula.io:3478?transport=udp">>}], Urls).

%% The environment hands back a list of code points, so a secret with any
%% character above 255 is not latin-1. coturn reads its secret as UTF-8 bytes,
%% and those are the bytes the HMAC must be keyed with.
mints_with_a_non_latin1_secret_test() ->
    Secret = [16#E9, 16#2713, $k],
    #{username := {text, Username}, credential := {text, Credential}} = mint(Secret),
    Key = unicode:characters_to_binary(Secret),
    ?assertEqual(base64:encode(crypto:mac(hmac, sha, Key, Username)), Credential).

username_is_a_near_future_unix_timestamp_test() ->
    #{username := {text, Username}} = mint("test-secret"),
    Expiry = binary_to_integer(Username),
    Now = erlang:system_time(second),
    ?assert(Expiry > Now),
    ?assert(Expiry =< Now + 3600).

%% A bare binary goes out as a CBOR BYTE string, and every non-BEAM caller
%% (macula-cli, macula-mcp, the Go/Rust/.NET/PHP SDKs, a mobile client) renders
%% it as 0x-hex. A TURN username or password in hex is useless to the ICE agent
%% that has to send it. Every string in the reply is tagged text.
no_bare_binary_leaves_in_the_reply_test() ->
    Reply = mint("test-secret"),
    ?assertEqual([], bare_binaries(Reply)).

%% The caller key the platform merges into a map payload is metadata, not
%% input, and nothing else in the payload changes what is minted.
payload_does_not_change_the_reply_shape_test() ->
    os:putenv(?SECRET_ENV, "test-secret"),
    {reply, Reply, undefined} =
        mint_turn_credential:handle_request(#{caller => <<0:256>>, <<"x">> => 1}, undefined),
    os:unsetenv(?SECRET_ENV),
    ?assertEqual([credential, ttl_seconds, urls, username], lists:sort(maps:keys(Reply))).

mint(Secret) ->
    os:putenv(?SECRET_ENV, Secret),
    {reply, Reply, undefined} = mint_turn_credential:handle_request(#{}, undefined),
    os:unsetenv(?SECRET_ENV),
    Reply.

bare_binaries(Map) when is_map(Map) ->
    lists:append([bare_binaries(V) || V <- maps:values(Map)]);
bare_binaries(List) when is_list(List) ->
    lists:append([bare_binaries(V) || V <- List]);
bare_binaries({text, Bin}) when is_binary(Bin) ->
    [];
bare_binaries(Bin) when is_binary(Bin) ->
    [Bin];
bare_binaries(_Other) ->
    [].
