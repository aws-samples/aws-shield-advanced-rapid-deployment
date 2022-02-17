# Checktags
Check tags is a reused parameter format designed to mimic the tag scoping abilities of AWS Firewall Manager tag scoping with customer solutions.  It is used by default for modules that mimic Shield Advanced security policies for unsupported resources and the config rule to auto-remediate proactive engagement health checks.

Checktags is a JSON list of tag names (key) or tag name(key)/value(s)(Value) that are evaluated against a given resource tag to determine if a resource is in scope.  One or more value of either tag name or tag name/value can be specified and are evaluated as "AND" statements.  If just a tag name is part of an item, the presence of the tag is determined regardless of the value.  When value is specified, then both the tag name (key) and exact key value (value) is checked.  tag key and tag value are case sensitive.  Below are several examples for a tag and tag value, just a tag, and both together.  Note when you specify this in the config file, you must have it be presented as a string (i.e. single quote the JSON)

## Examples

#### Example 1
Tag Named "AppName" with exact value "App1" exists.  This example is also formatted how a CloudFormation config file would expect this value to be provided

```
'[{“Key”: “AppName”,“Value”: “App1”}]'
```

#### Example 2
Tag Named "AppName" exists with any value
```
[
  {
      “Key”: “AppName”
  }
]
```

#### Example 3  
Tag name and value match as well as another tag exists regardless of value
```
[
  {
    “Key”: “AppName”,
    “Value”: “App1”
  },
  {
    “Key”: “Owner”
  }
]
```
