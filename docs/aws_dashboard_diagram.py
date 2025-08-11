from graphviz import Digraph

dot = Digraph("AWS_Cost_Management_Dashboard", format="png")
dot.attr(rankdir="LR", fontname="Arial")

# Helper: image node style
node_style = {
    "shape": "none",
    "fontsize": "10",
    "labelloc": "b",  # label below icon
    "margin": "0",
}

# Nodes with official AWS icons (update paths if you unzip somewhere else)
dot.node("UI", label="User\n(Web Browser)", image="aws-icons/General/User.png", **node_style)

dot.node("APIGW", label="Amazon API Gateway\n(REST API + CORS)", 
         image="aws-icons/NetworkingContentDelivery/Amazon-API-Gateway.png", **node_style)

dot.node("Lambda", label="AWS Lambda\n(Python 3.9 Cost-API)",
         image="aws-icons/Compute/AWS-Lambda.png", **node_style)

dot.node("CostExplorer", label="AWS Cost Explorer",
         image="aws-icons/ManagementGovernance/AWS-Cost-Explorer.png", **node_style)

dot.node("CUR", label="AWS Cost & Usage Reports\n(Stored in S3)",
         image="aws-icons/ManagementGovernance/AWS-Cost-and-Usage-Report.png", **node_style)

dot.node("DDB", label="Amazon DynamoDB\n(Cached & Historical Data)",
         image="aws-icons/Database/Amazon-DynamoDB.png", **node_style)

dot.node("IAM", label="AWS IAM\n(Permissions & Roles)",
         image="aws-icons/SecurityIdentityCompliance/AWS-Identity-and-Access-Management.png", **node_style)

dot.node("CW", label="Amazon CloudWatch\n(Metrics, Logs, Monitoring)",
         image="aws-icons/ManagementGovernance/Amazon-CloudWatch.png", **node_style)

# API Endpoints - no AWS icons, so simple notes
endpoints = {
    "Current": "GET /api/current",
    "Weekly": "GET /api/weekly",
    "Services": "GET /api/services",
    "Regions": "GET /api/regions",
}

for key, label in endpoints.items():
    dot.node(key, label, shape="note", fontsize="9", style="filled", fillcolor="#ffffff", margin="0.1")

# Edges - Data Flow
dot.edge("UI", "APIGW", label="HTTPS Requests")
dot.edge("APIGW", "Lambda", label="Invoke")
dot.edge("Lambda", "CostExplorer", label="Query Billing Metrics, Service Costs, Regional Data")
dot.edge("Lambda", "CUR", label="Access Historical Data")
dot.edge("Lambda", "DDB", label="Store/Retrieve Historical Trends, Cached Results")
dot.edge("Lambda", "CW", label="Logs")
dot.edge("APIGW", "CW", label="Metrics, Access Logs")
dot.edge("IAM", "Lambda", label="Permissions", style="dashed")
dot.edge("IAM", "CostExplorer", label="Permissions", style="dashed")

# Connect API Gateway to each endpoint
for key in endpoints.keys():
    dot.edge("APIGW", key)

# Render PNG (filename aws_cost_dashboard.png)
dot.render("aws_cost_dashboard", cleanup=True)
# Save the diagram to a file

