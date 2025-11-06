#!/usr/bin/env python3
"""
User management script for Image Labeling application
"""
import boto3
import sys
import argparse
from botocore.exceptions import ClientError


def get_user_pool_id():
    """Get User Pool ID from CloudFormation stack"""
    cf = boto3.client("cloudformation")
    try:
        response = cf.describe_stacks(StackName="image-labeling-stack")
        outputs = response.get("Stacks", [])[0].get("Outputs", [])
        for output in outputs:
            if "OutputKey" in output and output["OutputKey"] == "UserPoolId":
                return output.get("OutputValue", None)
    except KeyError:
        print("Error: UserPoolId not found in stack outputs")
        return None
    except ClientError as e:
        print(f"Error getting stack info: {e}")
        return None
    else:
        print("Error: Could not find UserPoolId output")
        return None


def invite_user(email, user_pool_id, temp_password=None):
    """Invite a new user to the application"""
    cognito = boto3.client("cognito-idp")

    try:
        params = {
            "UserPoolId": user_pool_id,
            "Username": email,
            "UserAttributes": [
                {"Name": "email", "Value": email},
                {"Name": "email_verified", "Value": "true"},
            ],
            "MessageAction": "EMAIL",
        }

        if temp_password:
            params["TemporaryPassword"] = temp_password
            params["MessageAction"] = "SUPPRESS"

        response = cognito.admin_create_user(**params)
        if "User" not in response:
            print(f"✗ Error inviting user {email}: No user returned in response")
            return False

        print(f"✓ User {email} invited successfully")
        if temp_password:
            print(f"  Temporary password: {temp_password}")
        return True

    except ClientError as e:
        print(f"✗ Error inviting user {email}: {e}")
        return False


def list_users(user_pool_id):
    """List all users in the user pool"""
    cognito = boto3.client("cognito-idp")

    try:
        response = cognito.list_users(UserPoolId=user_pool_id)

        if not response["Users"]:
            print("No users found")
            return

        print(f"Users in pool:")
        for user in response["Users"]:
            email = next(
                (
                    attr["Value"]
                    for attr in user["Attributes"]
                    if attr["Name"] == "email"
                ),
                "N/A",
            )
            status = user["UserStatus"]
            print(f"  {email} - {status}")

    except ClientError as e:
        print(f"Error listing users: {e}")


def delete_user(email, user_pool_id):
    """Delete a user from the user pool"""
    cognito = boto3.client("cognito-idp")

    try:
        response = cognito.admin_delete_user(UserPoolId=user_pool_id, Username=email)
        if response["ResponseMetadata"]["HTTPStatusCode"] != 200:
            print(f"✗ Error deleting user {email}: HTTP status code not 200")
            return False

        print(f"✓ User {email} deleted successfully")
        return True

    except ClientError as e:
        print(f"✗ Error deleting user {email}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Manage users for Image Labeling app")
    parser.add_argument(
        "action", choices=["invite", "list", "delete"], help="Action to perform"
    )
    parser.add_argument("--email", help="User email address")
    parser.add_argument("--password", help="Temporary password (optional)")
    parser.add_argument(
        "--user-pool-id", help="User Pool ID (auto-detected if not provided)"
    )

    args = parser.parse_args()

    # Get User Pool ID
    user_pool_id = args.user_pool_id or get_user_pool_id()
    if not user_pool_id:
        print("Error: Could not determine User Pool ID")
        sys.exit(1)

    if args.action == "invite":
        if not args.email:
            print("Error: --email required for invite action")
            sys.exit(1)
        invite_user(args.email, user_pool_id, args.password)

    elif args.action == "list":
        list_users(user_pool_id)

    elif args.action == "delete":
        if not args.email:
            print("Error: --email required for delete action")
            sys.exit(1)
        delete_user(args.email, user_pool_id)


if __name__ == "__main__":
    main()
