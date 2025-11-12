import argparse
from diagrams import Diagram, Cluster, Edge
from diagrams.aws.storage import S3
from diagrams.aws.compute import Lambda
from diagrams.aws.database import Dynamodb
from diagrams.aws.ml import Rekognition
from diagrams.aws.network import APIGateway
from diagrams.aws.mobile import Amplify
from diagrams.aws.management import Cloudwatch


_CLUSTER_GRAPH_ATTR = {"fontsize": "20"}


def _create_diagram(filename):
    def edge(label):
        return Edge(label=label, fontsize="18")

    with Diagram(
        "\nImage Labeler Architecture",
        show=False,
        direction="LR",
        filename=filename,
        graph_attr={"ratio": "0.5", "ranksep": "1.0", "fontsize": "48"},
        node_attr={"fontsize": "18", "width": "1.5", "height": "1.5"},
    ):
        user = Amplify("Web App", width="2.5", height="2.5", fontcolor="white")

        with Cluster("Storage", graph_attr=_CLUSTER_GRAPH_ATTR):
            s3 = S3("\n\nbluestone-image\n-labeling\n(uploads/ folder)")

        with Cluster("API Layer", graph_attr=_CLUSTER_GRAPH_ATTR):
            api = APIGateway("REST API", width="2.5", height="2.5", fontcolor="white")
            with Cluster("Lambda Functions", graph_attr=_CLUSTER_GRAPH_ATTR):
                upload_image = Lambda("\nupload_image")
                list_imgs = Lambda("\nlist_images")
                get_image = Lambda("\nget_image")
                get_labels = Lambda("\nget_labels")
                delete_image = Lambda("\ndelete_image")
                suggest_filters = Lambda("\nsuggest_filters")

        with Cluster("Image Processing", graph_attr=_CLUSTER_GRAPH_ATTR):
            process_image = Lambda("\nprocess_added_image")
            rekognition = Rekognition("\nRekognition")
            labels_table = Dynamodb(
                "\n\nimage_labels\n(PK: image_name, \nSK: label_name)"
            )

        with Cluster("Auto-Complete Processing", graph_attr=_CLUSTER_GRAPH_ATTR):
            update_prefix = Lambda("\n\nupdate_prefix\n_suggestions")
            label_counts = Dynamodb("\nlabel_counts")
            prefix_suggestions = Dynamodb("\nprefix_suggestions")

        scheduler = Cloudwatch("\n\nEventBridge\nScheduler")

        # User interactions
        user >> edge("get, upload, delete image") >> api
        user >> edge("get image labels") >> api
        user >> edge("get filter suggestions") >> api

        # API flows
        api >> upload_image >> s3
        api >> list_imgs >> edge("opt. with filters") >> labels_table
        api >> get_image >> s3
        api >> get_labels >> labels_table
        api >> delete_image >> s3
        api >> suggest_filters >> prefix_suggestions

        # Image processing flow
        s3 >> edge("S3 trigger") >> process_image
        process_image >> rekognition
        process_image >> labels_table
        process_image >> label_counts

        # Scheduled prefix update
        scheduler >> edge("periodic") >> update_prefix
        update_prefix >> label_counts
        update_prefix >> prefix_suggestions


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate architecture diagram")
    parser.add_argument(
        "filename",
        nargs="?",
        default="architecture",
        help="Output filename (without extension)",
    )
    args = parser.parse_args()
    _create_diagram(args.filename)
