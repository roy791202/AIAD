Feature: Product document compatibility characterization
  Current formats remain separate; this specification records behavior without approving a schema migration.

  Background:
    Given current product codecs and an isolated disposable document

  Rule: Representations remain explicit
    Scenario: BDD-DOC-01 Integrated scene carries XML sections
      When a current scene is encoded as .ess
      Then work, architecture and design appear inside one XML scene

    Scenario: BDD-DOC-02 Malformed XML cannot decode a scene
      Given malformed integrated XML
      When scene decoding is requested
      Then decoding provides no scene to apply

    Scenario: BDD-DOC-03 Legacy frontend roots remain a distinct compatibility path
      Given a supported legacy scene root and architecture root
      When frontend scene decoding is requested
      Then compatibility normalization is characterized separately from strict packet validation

  Rule: Typed design acceptance is explicit
    Scenario: BDD-DOC-04 Dedicated design cannot claim product acceptance
      Given .sgendesign JSON with product_pass true
      When dedicated design loading is requested
      Then loading reports an error

    Scenario: BDD-DOC-05 Project scene text remains project scoped
      Given a relative path escaping the project scene directory
      When scene persistence is requested
      Then the path is rejected

    Scenario: BDD-DOC-06 Strict packet cannot invent module identity
      Given an integrated scene with duplicate module identity
      When a readonly module packet is requested
      Then the packet request fails without changing the scene

  Rule: Characterization exposes unapproved guarantees
    Scenario: BDD-DOC-07 Late split-document failure is characterized
      Given valid work and architecture and malformed design input
      When the split scene is loaded
      Then the observed work and architecture states are recorded
      And no unverified rollback guarantee is reported

    Scenario: BDD-DOC-08 Unknown data fidelity is measured explicitly
      Given unknown document fields and scalar props "001", "true" and null
      When each applicable format is decoded and encoded
      Then preserved, converted and omitted values are reported per format
      And no full lossless-roundtrip result is inferred from fixture parsing
