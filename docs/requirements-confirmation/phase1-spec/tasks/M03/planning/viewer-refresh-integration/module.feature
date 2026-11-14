Feature: Explicit Viewer refresh
  Background:
    Given an authorized viewer with an existing detached preview
  Rule: Replace only after validated current snapshot and unchanged identity

    @VR-001
    Scenario: replace stale slot at full capacity; real revision above JS safe integer
      Given the bounded refresh fixture "VR-001"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-002
    Scenario: bounded current revision 0
      Given the bounded refresh fixture "VR-002"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-003
    Scenario: bounded current revision 18446744073709551615
      Given the bounded refresh fixture "VR-003"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-004
    Scenario: bounded current revision 7
      Given the bounded refresh fixture "VR-004"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-005
    Scenario: capture consumer changed
      Given the bounded refresh fixture "VR-005"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-006
    Scenario: delivery consumer changed
      Given the bounded refresh fixture "VR-006"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-007
    Scenario: capture window changed
      Given the bounded refresh fixture "VR-007"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-008
    Scenario: delivery window changed
      Given the bounded refresh fixture "VR-008"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-009
    Scenario: capture document changed
      Given the bounded refresh fixture "VR-009"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-010
    Scenario: delivery document changed
      Given the bounded refresh fixture "VR-010"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-011
    Scenario: capture session changed
      Given the bounded refresh fixture "VR-011"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-012
    Scenario: delivery session changed
      Given the bounded refresh fixture "VR-012"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-013
    Scenario: capture generation changed
      Given the bounded refresh fixture "VR-013"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-014
    Scenario: delivery generation changed
      Given the bounded refresh fixture "VR-014"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-015
    Scenario: capture closed
      Given the bounded refresh fixture "VR-015"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-016
    Scenario: delivery closed
      Given the bounded refresh fixture "VR-016"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-017
    Scenario: actual late observed revision 0
      Given the bounded refresh fixture "VR-017"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-018
    Scenario: actual late observed revision 18446744073709551615
      Given the bounded refresh fixture "VR-018"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-019
    Scenario: request conflicts current revision
      Given the bounded refresh fixture "VR-019"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-020
    Scenario: old retired UUID
      Given the bounded refresh fixture "VR-020"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-021
    Scenario: closed old session
      Given the bounded refresh fixture "VR-021"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-022
    Scenario: caller denied
      Given the bounded refresh fixture "VR-022"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-023
    Scenario: owner provider not ready
      Given the bounded refresh fixture "VR-023"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-024
    Scenario: actual provider CodecRejected
      Given the bounded refresh fixture "VR-024"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-025
    Scenario: actual provider ResourceLimit
      Given the bounded refresh fixture "VR-025"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-026
    Scenario: actual provider DependencyNotReady
      Given the bounded refresh fixture "VR-026"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-027
    Scenario: actual provider UnsupportedDocument
      Given the bounded refresh fixture "VR-027"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-028
    Scenario: actual provider AmbiguousStableId
      Given the bounded refresh fixture "VR-028"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-029
    Scenario: actual provider ParentMissing
      Given the bounded refresh fixture "VR-029"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-030
    Scenario: actual provider ParentCycle
      Given the bounded refresh fixture "VR-030"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-031
    Scenario: malformed provider outcome 'bogus'
      Given the bounded refresh fixture "VR-031"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-032
    Scenario: malformed provider outcome True
      Given the bounded refresh fixture "VR-032"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-033
    Scenario: malformed provider outcome {'code': 'CodecRejected', 'details': {'message': 1}}
      Given the bounded refresh fixture "VR-033"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-034
    Scenario: malformed provider outcome {'code': 'CodecRejected', 'details': {}, 'extra': True}
      Given the bounded refresh fixture "VR-034"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-035
    Scenario: reject provider trusted_local 'false'
      Given the bounded refresh fixture "VR-035"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-036
    Scenario: reject provider trusted_local 0
      Given the bounded refresh fixture "VR-036"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-037
    Scenario: reject provider trusted_local None
      Given the bounded refresh fixture "VR-037"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-038
    Scenario: reject provider trusted_local []
      Given the bounded refresh fixture "VR-038"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-039
    Scenario: reject provider ready 'false'
      Given the bounded refresh fixture "VR-039"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-040
    Scenario: reject provider ready 0
      Given the bounded refresh fixture "VR-040"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-041
    Scenario: reject provider ready None
      Given the bounded refresh fixture "VR-041"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-042
    Scenario: reject provider ready []
      Given the bounded refresh fixture "VR-042"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-043
    Scenario: typed capture revision
      Given the bounded refresh fixture "VR-043"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-044
    Scenario: typed capture revision
      Given the bounded refresh fixture "VR-044"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-045
    Scenario: typed capture generation
      Given the bounded refresh fixture "VR-045"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-046
    Scenario: typed capture closed
      Given the bounded refresh fixture "VR-046"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-047
    Scenario: typed capture session
      Given the bounded refresh fixture "VR-047"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-048
    Scenario: typed capture extra
      Given the bounded refresh fixture "VR-048"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-049
    Scenario: typed delivery revision
      Given the bounded refresh fixture "VR-049"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-050
    Scenario: typed delivery revision
      Given the bounded refresh fixture "VR-050"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-051
    Scenario: typed delivery generation
      Given the bounded refresh fixture "VR-051"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-052
    Scenario: typed delivery closed
      Given the bounded refresh fixture "VR-052"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-053
    Scenario: typed delivery session
      Given the bounded refresh fixture "VR-053"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-054
    Scenario: typed delivery extra
      Given the bounded refresh fixture "VR-054"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-055
    Scenario: request expected_revision ''
      Given the bounded refresh fixture "VR-055"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-056
    Scenario: request expected_revision '01'
      Given the bounded refresh fixture "VR-056"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-057
    Scenario: request expected_revision '-1'
      Given the bounded refresh fixture "VR-057"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-058
    Scenario: request expected_revision '1.0'
      Given the bounded refresh fixture "VR-058"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-059
    Scenario: request expected_revision '1e1'
      Given the bounded refresh fixture "VR-059"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-060
    Scenario: request expected_revision '18446744073709551616'
      Given the bounded refresh fixture "VR-060"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-061
    Scenario: request expected_revision '7\n'
      Given the bounded refresh fixture "VR-061"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-062
    Scenario: request expected_revision True
      Given the bounded refresh fixture "VR-062"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-063
    Scenario: request expected_revision 7
      Given the bounded refresh fixture "VR-063"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-064
    Scenario: request expected_revision None
      Given the bounded refresh fixture "VR-064"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-065
    Scenario: request preview_session ''
      Given the bounded refresh fixture "VR-065"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-066
    Scenario: request preview_session '22222222-2222-4222-8222-222222222222\n'
      Given the bounded refresh fixture "VR-066"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-067
    Scenario: request preview_session True
      Given the bounded refresh fixture "VR-067"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-068
    Scenario: request preview_session None
      Given the bounded refresh fixture "VR-068"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-069
    Scenario: unknown request field
      Given the bounded refresh fixture "VR-069"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-070
    Scenario: invalid projection preview_session
      Given the bounded refresh fixture "VR-070"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-071
    Scenario: invalid projection source_revision
      Given the bounded refresh fixture "VR-071"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-072
    Scenario: invalid projection expected_sequence
      Given the bounded refresh fixture "VR-072"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-073
    Scenario: invalid projection stale
      Given the bounded refresh fixture "VR-073"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-074
    Scenario: invalid projection extra
      Given the bounded refresh fixture "VR-074"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-075
    Scenario: invalid projection mock_state
      Given the bounded refresh fixture "VR-075"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-076
    Scenario: invalid projection capabilities
      Given the bounded refresh fixture "VR-076"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-077
    Scenario: duplicate node observation
      Given the bounded refresh fixture "VR-077"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-078
    Scenario: one slot exchange at count 1
      Given the bounded refresh fixture "VR-078"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-079
    Scenario: one slot exchange at count 3
      Given the bounded refresh fixture "VR-079"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-080
    Scenario: old sequence at maximum requires no increment
      Given the bounded refresh fixture "VR-080"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-081
    Scenario: missing request None
      Given the bounded refresh fixture "VR-081"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-082
    Scenario: missing request {}
      Given the bounded refresh fixture "VR-082"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-083
    Scenario: missing request {'preview_session': '11111111-1111-4111-8111-111111111111'}
      Given the bounded refresh fixture "VR-083"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-084
    Scenario: unknown provider record field
      Given the bounded refresh fixture "VR-084"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-085
    Scenario: node capability kind mismatch
      Given the bounded refresh fixture "VR-085"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed

    @VR-086
    Scenario: invalid typed number observation
      Given the bounded refresh fixture "VR-086"
      When the viewer explicitly refreshes
      Then the exact declared response and visible projection state are observed
