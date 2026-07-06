"""Campaign graph (PLAN 11.3).

Builds a graph whose edges are shared infrastructure: same hosting_ip, same
registrant_email, same kit_id, or co-mention in a report. Runs greedy modularity
community detection, keeps communities with >= 10 nodes, and labels each by its
majority campaign. The reveal: 455 indicators collapse to 3 campaigns + noise.

Pure networkx so the community count is provable in a test before the demo.
"""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx
import pandas as pd


@dataclass
class GraphResult:
    graph: nx.Graph
    communities: list[set]
    labeled: list[dict]  # [{size, campaign, campaign_name}]


def build_graph(iocs: pd.DataFrame, ioc_enrichment: pd.DataFrame) -> nx.Graph:
    """Build the shared-infrastructure graph over campaign indicators.

    Nodes are indicator values; edges connect indicators that share hosting IP,
    registrant email, or kit id. Only campaigns A-C carry enrichment, so noise
    and decoys stay as isolated nodes that fall out of the communities.
    """
    g = nx.Graph()
    enr = ioc_enrichment.dropna(subset=["indicator_value"])
    # Attach campaign for labeling.
    camp_by_ioc = dict(zip(iocs["indicator_value"], iocs["campaign_id"]))

    for _, row in enr.iterrows():
        g.add_node(row["indicator_value"], campaign=camp_by_ioc.get(row["indicator_value"]))

    # Group indicators by each shared attribute; connect within each group.
    for attr in ("hosting_ip", "registrant_email", "kit_id"):
        for value, group in enr.groupby(attr):
            members = list(group["indicator_value"])
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    g.add_edge(members[i], members[j])
    return g


def detect_communities(g: nx.Graph, min_size: int = 10) -> list[set]:
    """Greedy modularity communities, keeping those >= min_size."""
    from networkx.algorithms.community import greedy_modularity_communities

    if g.number_of_edges() == 0:
        return []
    comms = greedy_modularity_communities(g)
    return [set(c) for c in comms if len(c) >= min_size]


def label_communities(g: nx.Graph, communities: list[set], gt_campaigns: pd.DataFrame) -> list[dict]:
    """Label each community by its majority campaign id."""
    name_by_id = dict(zip(gt_campaigns["campaign_id"], gt_campaigns["name"]))
    out = []
    for comm in communities:
        camps = [g.nodes[n].get("campaign") for n in comm if g.nodes[n].get("campaign")]
        if not camps:
            continue
        majority = max(set(camps), key=camps.count)
        out.append({
            "size": len(comm),
            "campaign": majority,
            "campaign_name": name_by_id.get(majority),
        })
    return out


def build_campaign_graph(iocs: pd.DataFrame, ioc_enrichment: pd.DataFrame,
                         gt_campaigns: pd.DataFrame) -> GraphResult:
    g = build_graph(iocs, ioc_enrichment)
    communities = detect_communities(g)
    labeled = label_communities(g, communities, gt_campaigns)
    return GraphResult(graph=g, communities=communities, labeled=labeled)


def render_graph(result: GraphResult, hero_domain: str, out_path: str) -> str:
    """Draw the community graph with a spring layout, communities colored, hero
    starred. Instructor demo asset (PLAN 11.3). Returns the written path."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    g = result.graph
    pos = nx.spring_layout(g, seed=42)  # deterministic layout
    # Color nodes by community membership.
    palette = ["#00b39f", "#8b7cf6", "#ff6b5c", "#f6c65b"]
    color_by_node = {}
    for i, comm in enumerate(result.communities):
        for n in comm:
            color_by_node[n] = palette[i % len(palette)]
    node_colors = [color_by_node.get(n, "#3a4568") for n in g.nodes]

    fig, ax = plt.subplots(figsize=(11, 8))
    nx.draw_networkx_edges(g, pos, alpha=0.15, ax=ax)
    nx.draw_networkx_nodes(g, pos, node_color=node_colors, node_size=40, ax=ax)
    if hero_domain in g:
        nx.draw_networkx_nodes(g, pos, nodelist=[hero_domain], node_color="#ffffff",
                               node_shape="*", node_size=400, ax=ax)
    total = g.number_of_nodes()
    ax.set_title(f"{total} enriched indicators collapse to {len(result.communities)} campaigns")
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(out_path, dpi=140, facecolor="#0f1420")
    plt.close(fig)
    return out_path
