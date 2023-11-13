
# Shield Advance Rapid Deployment Helper Scripts

This collection of standalone Python scripts is designed to automate overhead of deletion and management of encountered failures in edge cases during the rapid deployment process.

## Scripts

### CheckDeletionFailure.py

**Purpose:** Checks the deletion status of AWS resources. It's designed to report on resources that may not have been successfully deleted.

**Usage:** Execute the script with necessary AWS credentials configured in your environment. The output will list any resources that have encountered deletion failures.

**Security Considerations:**

- Ensure AWS credentials used are properly secured and have the minimal required permissions to perform read-only actions on the resources.

### NonCompliantResourcesCounter.py

**Purpose:** Counts the number of non-compliant resources within your AWS environment, aiding in compliance and resource management.

**Usage:** Run the script with the appropriate permissions to list resources and their compliance status. The script will output a count of non-compliant resources.

**Security Considerations:**

- Utilize IAM roles with least privilege access.

### DeleteStacksPerStatus.py

**Purpose:** Deletes AWS stacks based on their status, automating the cleanup of stacks in certain states (e.g., DELETE_FAILED).

**Usage:** When executed, the script will remove stacks that match the status criteria specified within the script.

**Security Considerations:**

- Always run the script in a dry-run mode first, if available, to ensure no unintended deletions occur.

### DeleteRuleGroupsWAFv2.py

**Purpose:** Automates the deletion of WAFv2 rule groups in the FMS admin account.

**Usage:** Run the script to delete specified WAFv2 rule groups. Ensure the correct identifiers for the rule groups are specified.

**Security Considerations:**

- Always run the script in a dry-run mode first, if available, to ensure no unintended deletions occur.
- Implement logging to track changes made by the script for auditing purposes.

### DeleteFMSPolicies.py

**Purpose:** Facilitates the deletion of FMS policies in the FMS admin account, simplifying policy management.

**Usage:** Execute the script to remove FMS policies as defined by the script parameters.

**Security Considerations:**

- Always run the script in a dry-run mode first, if available, to ensure no unintended deletions occur.
- Always verify that the policies targeted for deletion are intended to be removed to avoid accidental loss of configurations.

## General Security Best Practices

- Test scripts in a controlled environment before running in production.

## Requirements

- Python 3.x
- boto3 library
- Properly configured AWS credentials with the necessary permissions

## Installation

Clone the repository or download the scripts directly. Ensure you have `boto3` installed:

- This script includes error handling to deal with potential issues during stack deletion.

- Always run the script in a dry-run mode first, if available, to ensure no unintended deletions occur.
