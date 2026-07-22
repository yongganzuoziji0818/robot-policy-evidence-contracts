"""Minimal, synthetic example; it does not reproduce a robot experiment."""

from robot_policy_evidence_contracts import certify_ranking


certificate = certify_ranking(
    estimates={"policy-a": 0.82, "policy-b": 0.74, "policy-c": 0.71},
    error_bounds={"policy-a": 0.03, "policy-b": 0.03, "policy-c": 0.03},
)

print("order:", certificate.ordered_policies)
for pair in certificate.adjacent_pairs:
    print(
        pair.higher,
        ">",
        pair.lower,
        "certified=" + str(pair.certified),
        "gap=" + str(round(pair.estimated_gap, 3)),
        "required>" + str(round(pair.required_gap, 3)),
    )
