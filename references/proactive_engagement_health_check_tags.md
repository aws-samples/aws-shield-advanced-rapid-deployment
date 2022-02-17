
## Resource Tags

#### probeFQDN
The [fully qualified domain name](https://docs.aws.amazon.com/Route53/latest/APIReference/API_UpdateHealthCheck.html#Route53-UpdateHealthCheck-request-FullyQualifiedDomainName) for an endpoint [Amazon Route 53 health](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/welcome-health-checks.html).  
__Type__: String  
__Default__:  
* __ALB__: `DNS Name of application load balancer. e.g. myALB-111111111.us-east-1.elb.amazonaws.com`  
* __EIP__:  `Public IPv4 DNS name per describe EC2 instance. e.g. ec2-11-222-333-44.compute-1.amazonaws.com`  
* __NLB__:  `DNS Name of network load balancer. e.g. myNLB-1a1a1a1a1a1a1a1a1a.elb.us-east-1.amazonaws.com`  
* __CloudFront__: `Amazon provide domain name for the given distribution.  e.g. d1234abcd.cloudfront.net`  

__AllowedPattern__:  See [fully qualified domain name](https://docs.aws.amazon.com/Route53/latest/APIReference/API_UpdateHealthCheck.html#Route53-UpdateHealthCheck-request-FullyQualifiedDomainName)

---

#### DDOSSNSTopic
A SNS topic ARN to be used as the target for CloudWatch alarms.  By default this will be when the specific resource has the metric AWS/DDoSProtection - DDoSDetected triggered.  
__Type__: String  
__Default__: `StackSet defined SNSTopic constructed ARN.`  
__AllowedPattern__: `arn:aws:sns:<region>:<accountId>:<topicName>`


---

#### probeSearchString
The string that you want Amazon Route 53 to search for in the response body from the specified resource. If the string appears in the response body, Route 53 considers the resource healthy.
See [Search String](https://docs.aws.amazon.com/Route53/latest/APIReference/API_UpdateHealthCheck.html#Route53-UpdateHealthCheck-request-SearchString)  
__Type__: String  
__Default__: `<none>`  

---

#### probeResourcePath
The path that you want Amazon Route 53 to request when performing health checks. The path can be any value for which your endpoint will return an HTTP status code of 2xx or 3xx when the endpoint is healthy, for example the file /docs/route53-health-check.html. You can also include query string parameters, for example, /welcome.html?language=jp&login=y.  See [Resource Path](https://docs.aws.amazon.com/Route53/latest/APIReference/API_UpdateHealthCheck.html#Route53-UpdateHealthCheck-request-ResourcePath)  \
__Type__: String  
__Default__: `<none>`  

---

#### probeType
The configuration of the endpoint probe type.  If probeSearchString is not null, the probe type will become the search string type.  e.g. specifying HTTPS will be configured as HTTPS_STR_MATCH when probeSearchString is not null.  See [Type](https://docs.aws.amazon.com/Route53/latest/APIReference/API_HealthCheckConfig.html#Route53-Type-HealthCheckConfig-Type)  
__Type__: String  
__Default__:  `HTTPS`  
__AllowedValues__:  
* `HTTP`
* `HTTPS`

---


#### probePort
The TCP port for the endpoint health check.
See [Port](https://docs.aws.amazon.com/Route53/latest/APIReference/API_HealthCheckConfig.html#Route53-Type-HealthCheckConfig-Port)  \
__Type__: String  
__Default__: `80 then probeType is HTTP | 443 then probeType is HTTPS`    
__AllowedValues__:  `1-65535`


---

#### probeHealthCheckRegions
Comma separated list of regions to complete Route 53 health checks.  At least three regions must be included. See [Route 53 supported regions](https://docs.aws.amazon.com/Route53/latest/APIReference/API_HealthCheckConfig.html#Route53-Type-HealthCheckConfig-Regions)  
__Type__: String  
__Default__:  `us-east-1,us-west-2,eu-west-1`  
__AllowedPattern__:  `List<String>`

---


#### metric1Name, metric2Name, metric3Name
The name of the cloudwatch metric for CloudWatch Alarm [1,2,3].  \
__Default__:  
* **ALB**:  `[HTTPCode_ELB_4XX_Count,HTTPCode_ELB_5XX_Count,TargetResponseTime]`  
* **EIP**:  `[CPUUtilization,NetworkIn,<not used>]`  
* **NLB**:  `[ActiveFlowCount,NewFlowCount,ProcessedBytes]`  
* **CloudFront**:  `[4xxErrorRate,5xxErrorRate,OriginLatency]`

__Type__: String  
__AllowedValues__:  \
&emsp;**ALB**  
* `ActiveConnectionCount`  
* `ConsumedLCUs`  
* `HTTPCode_ELB_4XX_Count`  
* `HTTPCode_ELB_5XX_Count`  
* `NewConnectionCount`  
* `ProcessedBytes`  
* `RejectedConnectionCount`  
* `RequestCount`  
* `TargetConnectionErrorCount`  
* `TargetResponseTime`  

&emsp;**EIP**  
* `CPUUtilization`  

&emsp;**NLB**  
* `ActiveFlowCount`  

&emsp;**CloudFront**  
* `4xxErrorRate`  

---


#### metric1Statistic, metric2Statistic, metric3Statistic
The CloudWatch Alarm statistic on the given metric [1,2,3]

__Default__  
* **ALB**:  `[Average,Average,Average]`  
* **EIP**:  `[Average,Sum,<not used>]`  
* **NLB**:  `[Average,Average,Sum]`  
* **CloudFront**:  `[Average,Average,Average]`  

__Type__: String  
__AllowedValues__\:  
* `Average`  
* `Sum`  
* `Minimum`  
* `Maximum`  
