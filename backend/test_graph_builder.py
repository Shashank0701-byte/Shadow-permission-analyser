from app.graph.graph_builder import load_dataset, build_graph

data = load_dataset("../dataset/iam_sample.json")
build_graph(data)

print("Graph built successfully!")