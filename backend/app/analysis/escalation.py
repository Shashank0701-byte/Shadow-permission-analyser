from app.graph.queries import get_user_permission_paths


def find_escalation_paths(user):
    """Analyse and return privilege-escalation paths for a user.

    Currently returns all reachable permission paths.  This is the
    correct place to add future enhancements such as:
      - filtering by resource sensitivity threshold
      - scoring paths by depth / number of ASSUME hops
      - detecting indirect / transitive privilege chains
    """
    paths = get_user_permission_paths(user)
    return paths
