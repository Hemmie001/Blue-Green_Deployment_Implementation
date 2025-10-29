# BLUE/GREEN_DEPLOYMENT_IMPLEMENTATION #
This repository contains the solution for the DevOps Intern Stage 2 Task, implementing a Blue/Green deployment strategy using Docker Compose and Nginx configured for automatic failover and manual pool promotion.

    
## 1. Project Overview ##
The core objective is to place two Node.js services (Blue and Green) behind an Nginx proxy configured as a primary/backup pair. The system must achieve:

### a) Default State: ###
All traffic routes to Blue.

### b) Auto-Failover: On Blue's failure (timeout/5xx), Nginx automatically retries the request to Green within the same client connection, ensuring zero failed requests for the client.

Manual Toggle: Support for promoting Green to be the new active primary pool via configuration change.

Header Forwarding: Nginx must forward application headers (X-App-Pool, X-Release-Id) unchanged.

2. Repository Structure

