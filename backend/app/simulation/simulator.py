"""IAM dataset simulator.

Generates realistic, randomised IAM structures that always contain
**at least one hidden privilege-escalation path**.

A guaranteed escalation chain is injected into every dataset::

    Intern_A → InternRole → DevRole → AdminRole → ProductionDB (sensitivity 5)

Additional users, roles, resources, and relationships are generated
randomly around this core chain to create noise and make the
escalation path non-obvious.
"""

import random
import string
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configurable pools
# ---------------------------------------------------------------------------

_USER_PREFIXES = ["Intern", "Dev", "QA", "Ops", "Support", "Analyst", "Manager"]
_ROLE_TEMPLATES = ["Viewer", "Editor", "Deployer", "Auditor", "Tester", "Monitor"]
_RESOURCE_TEMPLATES = [
    ("ProductionDB", 5),
    ("StagingDB", 3),
    ("LogsBucket", 2),
    ("SecretVault", 5),
    ("CICDPipeline", 4),
    ("AnalyticsDW", 3),
    ("BackupStorage", 2),
    ("AdminConsole", 5),
    ("MonitoringDashboard", 1),
    ("ConfigStore", 4),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_dataset(
    num_extra_users: int = 5,
    num_extra_roles: int = 4,
    num_extra_resources: int = 3,
    seed: int | None = None,
) -> dict:
    """Generate a randomised IAM dataset with a guaranteed escalation path.

    Parameters
    ----------
    num_extra_users : int
        Number of additional random users beyond the escalation chain actors.
    num_extra_roles : int
        Number of additional random roles beyond the escalation chain roles.
    num_extra_resources : int
        Number of additional random resources beyond ``ProductionDB``.
    seed : int or None
        Optional RNG seed for reproducibility.

    Returns
    -------
    dict
        A dataset compatible with ``graph_builder.build_graph()``.
    """
    if seed is not None:
        random.seed(seed)

    # --- guaranteed escalation chain -----------------------------------------
    escalation_users = ["Intern_A"]
    escalation_roles = ["InternRole", "DevRole", "AdminRole"]
    escalation_resource = {"name": "ProductionDB", "sensitivity": 5}

    # --- extra users ---------------------------------------------------------
    extra_users = _random_names(_USER_PREFIXES, num_extra_users)
    all_users = list(dict.fromkeys(escalation_users + extra_users))

    # --- extra roles ---------------------------------------------------------
    extra_roles = _random_names(_ROLE_TEMPLATES, num_extra_roles, suffix="Role")
    all_roles = list(dict.fromkeys(escalation_roles + extra_roles))

    # --- extra resources -----------------------------------------------------
    available = [r for r in _RESOURCE_TEMPLATES if r[0] != "ProductionDB"]
    chosen = random.sample(available, min(num_extra_resources, len(available)))
    all_resources = [escalation_resource] + [
        {"name": name, "sensitivity": sens} for name, sens in chosen
    ]

    # --- relationships -------------------------------------------------------
    assignments: list[list[str]] = []
    assume: list[list[str]] = []
    permissions: list[list[str]] = []

    # guaranteed chain: Intern_A → InternRole → DevRole → AdminRole → ProductionDB
    assignments.append(["Intern_A", "InternRole"])
    assume.append(["InternRole", "DevRole"])
    assume.append(["DevRole", "AdminRole"])
    permissions.append(["AdminRole", "ProductionDB"])

    # random assignments (other users → random roles)
    for user in extra_users:
        role = random.choice(all_roles)
        assignments.append([user, role])

    # random assume relationships (some roles can assume others)
    for _ in range(random.randint(1, max(1, num_extra_roles))):
        r1, r2 = random.sample(all_roles, 2)
        assume.append([r1, r2])

    # random permissions (roles → resources)
    resource_names = [r["name"] for r in all_resources]
    for role in extra_roles:
        if random.random() < 0.6:
            permissions.append([role, random.choice(resource_names)])

    # deduplicate
    assignments = _dedupe(assignments)
    assume = _dedupe(assume)
    permissions = _dedupe(permissions)

    dataset = {
        "users": all_users,
        "roles": all_roles,
        "resources": all_resources,
        "assignments": assignments,
        "assume": assume,
        "permissions": permissions,
    }

    logger.info(
        "Simulated dataset: %d users, %d roles, %d resources, "
        "%d assignments, %d assume, %d permissions.",
        len(all_users),
        len(all_roles),
        len(all_resources),
        len(assignments),
        len(assume),
        len(permissions),
    )
    return dataset


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _random_names(
    prefixes: list[str],
    count: int,
    suffix: str = "",
) -> list[str]:
    """Generate *count* unique random names from *prefixes*."""
    names: set[str] = set()
    while len(names) < count:
        prefix = random.choice(prefixes)
        tag = "".join(random.choices(string.ascii_uppercase + string.digits, k=3))
        name = f"{prefix}_{tag}{suffix}" if suffix else f"{prefix}_{tag}"
        names.add(name)
    return list(names)


def _dedupe(pairs: list[list[str]]) -> list[list[str]]:
    """Remove duplicate [a, b] pairs while preserving order."""
    seen: set[tuple[str, str]] = set()
    result: list[list[str]] = []
    for pair in pairs:
        key = (pair[0], pair[1])
        if key not in seen:
            seen.add(key)
            result.append(pair)
    return result
