# Cover letter — Discover Computing

*(Submit through Snapp with the manuscript; select article type "Research" and the topical collection named below. Replace the `[[TBC:*]]` tokens before submission.)*

---

Dear Editors,

Please consider the enclosed manuscript, *"CertGate: finite-sample certified selective prediction for multi-site clinical risk models, with label-shift robustness and explainable abstention,"* for the topical collection **"Intelligent Medicine: Machine Learning and Explainable AI for Next-Generation Healthcare."**

Clinical risk models are routinely deployed across many hospitals, yet the selective-prediction guarantees that govern when such a model may answer are almost always written at the record level — and records cluster by hospital, so those guarantees overrun their stated confidence exactly where multi-site deployment needs them. The manuscript presents a selective-prediction gate whose certificate treats the hospital, rather than the record, as the unit of statistical independence; carries a label-shift correction whose estimation uncertainty is budgeted inside the guarantee; and attaches an exact attribution to every answer and every abstention, so a deferred case is explained to the clinician who receives it rather than silently withheld. Alongside a synthetic validation grid with verified-falsifiable negative controls, the method is demonstrated end to end on eICU-CRD v2.0 (164,322 ICU stays across 207 US hospitals) under an analysis protocol frozen and committed before the extract was read, with the certificate's disclosures — what it bounds, what it declines to bound, and how the answered set's composition differs from its pool — reported beside every certified number. Comparator bounds, stress arms, and power frontiers on the same synthetic atoms delimit what the certificate can and cannot deliver at realistic hospital counts. On the real cohort the explanation layer is read as well as built: the abstention driver is stable and clinically legible — the Glasgow motor score on every re-split, with oxygenation and airway status behind it — and the manuscript states which part of that reading survives the attribution value-function choice and which does not. The subgroup analysis reports the certificate's cost as a service-equity question: the budget is met in every resolvable subgroup, but by deferring the oldest and sickest most often. We believe this combination — certified uncertainty quantification, out-of-distribution robustness under a named assumption, and explainability designed for clinical auditability — sits squarely within the collection's *Fairness, Causality, Robustness, and Trustworthy ML* topic, and that the deferral report and its two-register explanation page speak to the collection's emphasis on explanation as a transparency requirement and a teaching aid.

One request on refereeing. The certificate's validity rests on a betting-martingale argument (Supplementary Information A.1–A.2) that a clinical-AI referee may reasonably decline to check; we would be grateful if one referee could be drawn from distribution-free uncertainty quantification or sequential inference, so that the load-bearing part of the paper is reviewed by someone positioned to find its errors.

The eICU-CRD data were accessed under PhysioNet's credentialed license and Data Use Agreement; the database is de-identified under the HIPAA Safe Harbor provision (certified by Privacert, HIPAA Certification no. 1031219-2), and this retrospective secondary analysis required no additional ethics approval. All released artifacts derived from it are aggregate-only. The complete implementation and every synthetic result are reproducible from the public repository named in the manuscript.

This manuscript is original, has not been published previously, and is not under consideration elsewhere. The author has approved the submission and has no competing interests to declare.

Thank you for your consideration.

Sincerely,

Tony Zhang
Department of Physiology and Pharmacology, Western University, London, Ontario, Canada
tzhan659@uwo.ca
