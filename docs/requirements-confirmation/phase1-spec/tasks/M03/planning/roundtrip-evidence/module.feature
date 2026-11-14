Feature: Design data preservation across approved boundaries

  @M03-RT-01
  Scenario: M03-RT-01
    Given all known format/meta/node properties
    When read and save design data
    Then supported values semantically equal

  @M03-RT-02
  Scenario: M03-RT-02
    Given current UI design has numeric v/h guide arrays
    When read and save through approved codec
    Then both guide arrays preserved or unsupported source explicitly refused before any formal write

  @M03-RT-03
  Scenario: M03-RT-03
    Given current UI design has gridSize and formSize
    When read and save
    Then grid/form sizing retained without silent defaults

  @M03-RT-04
  Scenario: M03-RT-04
    Given nodes have scope and uiExclusive flags
    When read and save
    Then ownership-related node flags preserved or unsupported input refused

  @M03-RT-05
  Scenario: M03-RT-05
    Given props has nested object/array/bool/null values
    When read and save
    Then supported property tree semantically unchanged

  @M03-RT-06
  Scenario: M03-RT-06
    Given new root property not in frozen contract
    When request save
    Then not accepted with silent data loss; exact preserve-vs-reject policy requires future precise review

  @M03-RT-07
  Scenario: M03-RT-07
    Given new node property not in frozen contract
    When request save
    Then not accepted with silent data loss; exact policy requires precise review

  @M03-RT-08
  Scenario: M03-RT-08
    Given codec refuses unsupported/malformed input
    When request save
    Then formal target/SSOT/dirty state unchanged

  @M03-RT-09
  Scenario: M03-RT-09
    Given design tries product_pass=true
    When read/serialize
    Then reject, never produce formal PASS

  @M03-RT-10
  Scenario: M03-RT-10
    Given Editor selection and isolated Viewer mock use same source
    When activate/select
    Then view-only state does not rewrite authoritative document

  @M03-RT-11
  Scenario: M03-RT-11
    Given source revision changes during preview build
    When publish preview
    Then reject stale projection and retain visibly labelled previous version

  @M03-RT-12
  Scenario: M03-RT-12
    Given actual Windows native editor saves design with guides
    When close/reopen design
    Then same fields restored; this is pending, no native proof from console probe

