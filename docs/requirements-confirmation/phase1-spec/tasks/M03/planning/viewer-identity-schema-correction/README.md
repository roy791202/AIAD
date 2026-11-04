# VIS-RF1 bounded schema correction

Author: /root/m03_identity_schema_correction. Scope: new candidate only.

Run `python -B checker.py` from D:/AIAD. This is author document verification, not independent acceptance or a valid production RED/GREEN cycle.

The five changed properties are generation and four UUIDs. The UUID grammar is lower-case UUID v4 with RFC variant 8/9/a/b, exactly matching existing CLOSE.identity. Generation is canonical ASCII decimal 0 through 18446744073709551615. Existing refresh request schema $ref targets are resolved and copied inline; no new definitions or reference paths are introduced. Strict end uses (?![\s\S]), never terminal dollar.

All other observation properties and root closure are unchanged. Nonempty consumer/window/root/epoch strings retain the existing guard domain, including newline and Unicode strings. Schema-valid values may still fail admission for dead/revoked observations or identity mismatch. Full-root grammar parity is the claim; authorization success parity is not.

Original document_model.py is imported at its original path, so mapper, policies, reducers and dependency paths remain bytewise unchanged. No schema-body/model redesign, public command schema modification, native provider API adoption, or VIS-D1..D5 approval occurs. Source authority: M01/planning/s2-green/source-current.json (796 hashes, historical 31babe); actual HEAD 5b709343a890503ebbe24a802e43cda5647df124. Frozen 513 inputs allow only separately classified board-management difference.

Expected RED: the original parsed schema accepts the six independent-review counterexamples while the unchanged guard rejects them. This is historical document differential reproduction, not product TDD RED. Corrected schema rejects all six. New vectors cover root/type/required/unknown properties, LF/CR/Unicode, UUID version/variant/casing, leading zero and exact range boundaries.

Pending automation: independent bounded review; full Draft2020 validation; native provider/fence/runtime validation; product build, product RED, module/system acceptance. B058-B060 remain separate. Parent Yellow and REPLAN_REQUIRED remain.
