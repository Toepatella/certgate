# Cover letter — Discover Computing

*(Submit through Snapp with the manuscript; select article type "Research" and the topical collection named below. Replace the `[[TBC:*]]` tokens before submission.)*

---

Dear Editors,

Please consider the enclosed manuscript, *"CertGate: finite-sample certified selective prediction for multi-site clinical risk models, with label-shift robustness and explainable abstention,"* for the topical collection **"Intelligent Medicine: Machine Learning and Explainable AI for Next-Generation Healthcare."**

Clinical risk models are routinely deployed across many hospitals, yet the selective-prediction guarantees that govern when such a model may answer are almost always written at the record level — and records cluster by hospital, so those guarantees overrun their stated confidence exactly where multi-site deployment needs them. The manuscript presents a selective-prediction gate whose certificate treats the hospital, rather than the record, as the unit of statistical independence; carries a label-shift correction whose estimation uncertainty is budgeted inside the guarantee; and attaches an exact attribution to every answer and every abstention, so a deferred case is explained to the clinician who receives it rather than silently withheld. Alongside a synthetic validation grid with verified-falsifiable negative controls, the method is demonstrated end to end on eICU-CRD v2.0 (164,322 ICU stays across 207 US hospitals) under an analysis protocol frozen and committed before the extract was read, with the certificate's disclosures — what it bounds, what it declines to bound, and how the answered set's composition differs from its pool — reported beside every certified number. Comparator bounds, stress arms, and power frontiers on the same synthetic atoms delimit what the certificate can and cannot deliver at realistic hospital counts. We believe this combination of certified uncertainty quantification, distribution-shift robustness, and explainability aimed at clinical auditability sits squarely within the collection's scope.

The eICU-CRD data were accessed under PhysioNet's credentialed license and Data Use Agreement; the database is de-identified under the HIPAA Safe Harbor provision (certified by Privacert, HIPAA Certification no. 1031219-2), and this retrospective secondary analysis required no additional ethics approval. All released artifacts derived from it are aggregate-only. The complete implementation and every synthetic result are reproducible from the public repository named in the manuscript.

This manuscript is original, has not been published previously, and is not under consideration elsewhere. All authors have approved the submission and have no competing interests to declare. [[TBC:adjust-if-competing-interests-exist]]

Thank you for your consideration.

Sincerely,

[[TBC:corresponding-name]]
[[TBC:affiliation]]
[[TBC:corresponding-email]]
