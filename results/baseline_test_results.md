# SecureBERT 2.0 Base Model — Baseline Test Results

**Date:** 2025-05-01  
**Model:** `cisco-ai/SecureBERT2.0-base` (no fine-tuning)  
**Purpose:** Evaluate how the base encoder handles raw vs. standardized alert formats before any fine-tuning is applied.

---

## Test 1: Interactive — Process Creation Alerts

Two structurally identical endpoint alerts differing only in the process name:

| Alert | Input | Tokens |
|-------|-------|--------|
| 1 | `[endpoint] A new process has been created. new_process=cmd.exe account=BSTOLL-L$` | 28 |
| 2 | `[endpoint] A new process has been created. new_process=dllhost.exe account=BSTOLL-L$` | 29 |

**Cosine Similarity: 0.9978**

### Analysis

- `cmd.exe` is a LOLBin (T1059.003) frequently abused in attack chains — high suspicion when spawned by a machine account.
- `dllhost.exe` (COM Surrogate) is routine system behavior — low suspicion.
- The base model treats them as essentially identical, keying on sentence structure rather than the security-relevant process name.
- **Conclusion:** Base embeddings capture linguistic similarity, not threat-level differentiation.

---

## Test 2: Batch — Raw vs. Standardized Alerts (7 Events × 2 Formats)

Seven security events spanning the full Navitas tool stack, each represented in raw (unstructured) and standardized (pipe-delimited) format.

### Alert Inventory

| Alert # | Format | Source | Event Type |
|---------|--------|--------|------------|
| 2 | Raw | Syslog | SSH auth failure |
| 3 | Raw | Wazuh JSON | SSH auth failure |
| 4 | Raw | Trellix CEF | Malware detected |
| 5 | Raw | CrowdStrike | Suspicious PowerShell |
| 6 | Raw | Purview DLP | PII copy to USB |
| 7 | Raw | CloudTrail JSON | Failed console login |
| 8 | Raw | Netskope | PHI upload blocked |
| 10 | Std | Syslog | SSH auth failure |
| 11 | Std | Wazuh | SSH auth failure |
| 12 | Std | Trellix EX | Malware detected |
| 13 | Std | CrowdStrike | Suspicious PowerShell |
| 14 | Std | Purview DLP | PII copy to USB |
| 15 | Std | CloudTrail | Failed console login |
| 16 | Std | Netskope | PHI upload blocked |

*(Alerts 1 and 9 were comment lines processed as text — excluded from analysis.)*

### Finding 1: Standardized alerts cluster tightly on FORMAT, not meaning

Similarity range within standardized alerts (10–16): **0.9224 – 0.9753**

These are fundamentally different security events (auth failure, malware, exfiltration, policy violation) yet the model sees them as near-identical because they share the `source= | event_type= | severity=` template.

### Finding 2: Same event in different formats shows moderate divergence

| Event | Raw Alert | Std Alert | Similarity |
|-------|-----------|-----------|------------|
| Syslog SSH failure | 2 | 10 | 0.8344 |
| Wazuh SSH failure | 3 | 11 | 0.7861 |
| Trellix malware | 4 | 12 | 0.8649 |
| CrowdStrike PowerShell | 5 | 13 | 0.8215 |
| Purview DLP violation | 6 | 14 | 0.8268 |
| CloudTrail auth failure | 7 | 15 | 0.8575 |
| Netskope exfil blocked | 8 | 16 | 0.8494 |

**Average same-event cross-format similarity: 0.8344**

The base model considers the same event in two formats to be *more different* than two unrelated events that share the same format.

### Finding 3: Raw alerts show broader similarity spread

Similarity range within raw alerts (2–8): **0.7897 – 0.9366**

More variance here because each source uses a different syntax (syslog, JSON, CEF, plaintext), but the model is still responding primarily to format tokens rather than security semantics.

---

## Key Conclusions

1. **Base SecureBERT is a linguistic encoder, not a security encoder.** It clusters on surface-level text patterns (format, punctuation, template structure) rather than security-relevant content.

2. **Format noise dominates semantic content.** Standardization paradoxically makes the model *less* able to distinguish between different event types because it normalizes the very tokens the model relies on for differentiation.

3. **Fine-tuning is mandatory.** To produce embeddings where threat-relevant features (process names, event types, severity context) outweigh format similarity, the model must be trained on labeled security data with explicit threat/benign signal.

4. **Implication for pipeline design:** The standardized format is still correct for the preprocessing pipeline — it's essential for consistent feature extraction and human readability. But the model needs fine-tuning to learn that `event_type=malware_detected` and `event_type=authentication_failure` are semantically distant despite being syntactically adjacent.

---

## Raw Similarity Matrix

```
                           [1]     [2]     [3]     [4]     [5]     [6]     [7]     [8]     [9]    [10]    [11]    [12]    [13]    [14]    [15]    [16]
  Alert 1                 1.0000  0.8852  0.8187  0.8769  0.8564  0.8879  0.8224  0.9098  0.9727  0.8015  0.7874  0.7613  0.7759  0.7631  0.7839  0.7987
  Alert 2                 0.8852  1.0000  0.7897  0.9157  0.8327  0.9107  0.8183  0.8878  0.8814  0.8344  0.8380  0.8159  0.8085  0.7978  0.7957  0.8240
  Alert 3                 0.8187  0.7897  1.0000  0.8362  0.8642  0.8275  0.8787  0.8496  0.8218  0.8145  0.7861  0.7735  0.8006  0.7906  0.8147  0.7923
  Alert 4                 0.8769  0.9157  0.8362  1.0000  0.8661  0.9072  0.8675  0.8968  0.8783  0.8797  0.8735  0.8649  0.8481  0.8379  0.8486  0.8572
  Alert 5                 0.8564  0.8327  0.8642  0.8661  1.0000  0.8962  0.8392  0.9252  0.8620  0.8256  0.7949  0.7621  0.8215  0.7835  0.8187  0.7948
  Alert 6                 0.8879  0.9107  0.8275  0.9072  0.8962  1.0000  0.8152  0.9366  0.9020  0.8332  0.8343  0.8088  0.8239  0.8268  0.8093  0.8386
  Alert 7                 0.8224  0.8183  0.8787  0.8675  0.8392  0.8152  1.0000  0.8453  0.8143  0.8583  0.8248  0.8038  0.8269  0.8076  0.8575  0.8178
  Alert 8                 0.9098  0.8878  0.8496  0.8968  0.9252  0.9366  0.8453  1.0000  0.9126  0.8438  0.8351  0.8053  0.8450  0.8215  0.8373  0.8494
  Alert 9                 0.9727  0.8814  0.8218  0.8783  0.8620  0.9020  0.8143  0.9126  1.0000  0.7921  0.7819  0.7535  0.7677  0.7583  0.7739  0.7879
  Alert 10                0.8015  0.8344  0.8145  0.8797  0.8256  0.8332  0.8583  0.8438  0.7921  1.0000  0.9606  0.9297  0.9485  0.9382  0.9753  0.9346
  Alert 11                0.7874  0.8380  0.7861  0.8735  0.7949  0.8343  0.8248  0.8351  0.7819  0.9606  1.0000  0.9614  0.9505  0.9585  0.9497  0.9571
  Alert 12                0.7613  0.8159  0.7735  0.8649  0.7621  0.8088  0.8038  0.8053  0.7535  0.9297  0.9614  1.0000  0.9356  0.9542  0.9224  0.9422
  Alert 13                0.7759  0.8085  0.8006  0.8481  0.8215  0.8239  0.8269  0.8450  0.7677  0.9485  0.9505  0.9356  1.0000  0.9528  0.9550  0.9528
  Alert 14                0.7631  0.7978  0.7906  0.8379  0.7835  0.8268  0.8076  0.8215  0.7583  0.9382  0.9585  0.9542  0.9528  1.0000  0.9422  0.9619
  Alert 15                0.7839  0.7957  0.8147  0.8486  0.8187  0.8093  0.8575  0.8373  0.7739  0.9753  0.9497  0.9224  0.9550  0.9422  1.0000  0.9382
  Alert 16                0.7987  0.8240  0.7923  0.8572  0.7948  0.8386  0.8178  0.8494  0.7879  0.9346  0.9571  0.9422  0.9528  0.9619  0.9382  1.0000
```
