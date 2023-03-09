
from osmnx._errors import EmptyOverpassResponse
import osmnx as ox
from osmnx import utils_graph, distance, downloader,graph
 
# del original _create_graph
def create_branch_graph(response_json_branch, retain_all=False, bidirectional=True):
    """
    Create a networkx MultiDiGraph from Overpass API responses.
    Adds length attributes in meters (great-circle distance between endpoints)
    to all of the graph's (pre-simplified, straight-line) edges via the
    `distance.add_edge_lengths` function.
    Parameters
    ----------
    response_json_branch : dict
        dicts of JSON response for a route branch from the Overpass API
    retain_all : bool
        if True, return the entire graph even if it is not connected.
        otherwise, retain only the largest weakly connected component.
    bidirectional : bool
        if True, create bi-directional edges for one-way streets
    Returns
    -------
    G : networkx.MultiDiGraph
    """
    print("Creating graph from downloaded OSM data...")

    # create the graph as a MultiDiGraph and set its meta-attributes
    metadata = {
        "created_date": ox.utils.ts(),
        "crs": "epsg:4326",
        "line_name": response_json_branch['tags']['name'],
        "headway":response_json_branch['tags']['to']
    }
    G = nx.MultiDiGraph(**metadata)

    # query nodes and ways to get xy coords
    nodes = {}
    paths = {}
    nodes_temp, paths_temp = query_branch_nodes_paths(response_json_branch)
    nodes.update(nodes_temp)
    paths.update(paths_temp)

    # add each osm node to the graph
    for node, data in nodes.items():
        G.add_node(node, **data)

    # add each osm way (ie, a path of edges) to the graph
    graph._add_paths(G, paths.values(), bidirectional)

    # retain only the largest connected component if retain_all is False
    if not retain_all:
        G = utils_graph.get_largest_component(G)

    print(f"Created graph with {len(G)} nodes and {len(G.edges)} edges")

    # add length (great-circle distance between nodes) attribute to each edge
    if len(G.edges) > 0:
        G = distance.add_edge_lengths(G)

    return G
    
def query_branch_nodes_paths(response_json_branch):
    """
    Create a set of nodes and paths belonging to a relation in Osmnx schema
    (the one _parse_nodes_paths outpus) from Overpass API responses.  
    Parameters
    ----------
    response_json_branch : dict
        dicts of JSON response for a route branch from the Overpass API
    Returns
    -------
    nodes, paths : tuple of dicts
        dicts' keys = osmid and values = dict of attributes
    """ 

    overpass_settings = downloader._make_overpass_settings()

    # get path ids
    path_ids = [m['ref'] if m['type']=='way'else None for m in response_json_branch['members']]
    path_ids = list(filter(lambda item: item is not None, path_ids))
    path_ids = ','.join(map(str,path_ids))

    query_str = f"{overpass_settings};(way(id:{path_ids});>;);out;"
    response_json = downloader.overpass_request(data={"data": query_str})

    nodes, paths = graph._parse_nodes_paths(response_json)
    return nodes, paths

def query_public_transport_box(north,south,east,west):
    """
    Queries OSMN public transportation relations
    from a boungind box
    
    Parameters
    ----------
    north : float
        northern latitude of bounding box
    south : float
        southern latitude of bounding box
    east : float
        eastern longitude of bounding box
    west : float
        western longitude of bounding box

    Returns
    -------
    nodes, paths : tuple of dicts
        dicts' keys = osmid and values = dict of attributes
    """ 

    bbox = (str(south) + "," +
            str(west) + "," +
            str(north) + "," +
            str(east))
    
    tags = '["public_transport:version" = "2"]'

    query_str = """
        [out:json];
        (
        relation%s(%s);
        relation[type=route_master](br.routes);
        way(r.routes);
        node(w);
        ( .routes;.masters;._; );
        );out body;""" % (tags, bbox)
    response_json_branches = ox.downloader.overpass_request(data={'data':query_str})
        # make sure we got data back from the server request(s)
    if not 'elements' in response_json_branches:  # pragma: no cover
        raise EmptyOverpassResponse("There are no data elements in the response JSON")
    else:
        response_json_branches = response_json_branches['elements']
    return response_json_branches