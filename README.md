# StayNest 🏡 — Property Booking Platform on AWS

A cloud-native property rental listing platform (Airbnb-style), built and deployed as a full AWS architecture — from a single EC2 instance to a load-balanced, auto-scaling, monitored production setup.

> Built for INT-330 (Managing Cloud Solutions) at Lovely Professional University. This repo documents the full architecture, decisions, and debugging process. **The live environment has since been decommissioned to avoid ongoing AWS charges** — see [Status](#status) below.

---

## Status

🔴 **Not currently deployed.** The infrastructure was torn down after course completion to stop AWS billing. This repo is a full record of the working system: architecture, IaC-equivalent configs, code, and screenshots from when it was live.

---

## What it does

StayNest lets visitors:
- Browse property listings (6 curated stays across Goa, India) with photos, pricing, and amenities
- View individual property details
- Submit booking requests through a booking form
- Receive automatic email confirmations
- (Admin) View a live, password-protected dashboard of all bookings, revenue, and guest stats

## Screenshots

| Homepage | Listings | Admin Dashboard |
|---|---|---|
| Hero section with search | Property cards with pricing | Live booking table + stats |

*(Add exported screenshots from the report into a `/screenshots` folder and embed them here, e.g. `![Homepage](screenshots/homepage.png)`)*

---

## Architecture

```
                         ┌────────────────────────┐
                         │  Application Load       │
   User ───────────────► │  Balancer (staynest-    │
                         │  asg-1)                  │
                         └───────────┬──────────────┘
                                     │
                         ┌───────────▼──────────────┐
                         │  Auto Scaling Group        │
                         │  (staynest-asg, 1–3 x      │
                         │  t3.micro, Nginx + Flask)  │
                         └───────────┬──────────────┘
                                     │
                ┌────────────────────┼─────────────────────┐
                │                    │                      │
        ┌───────▼───────┐   ┌────────▼────────┐   ┌─────────▼─────────┐
        │  CloudFront    │   │  RDS MySQL       │   │  SNS + SES         │
        │  CDN → S3      │   │  (staynest-db)   │   │  (owner alerts +   │
        │  (property     │   │  booking records │   │  customer emails)  │
        │  images)       │   │                  │   │                    │
        └────────────────┘   └──────────────────┘   └────────────────────┘

        CloudWatch monitors EC2 CPU → triggers SNS alarm at >80%
        All resources live inside the default VPC; IAM user has read-only access
```

Classic three-tier pattern:
- **Presentation:** Nginx on EC2 (behind an ALB + Auto Scaling Group)
- **Application:** Flask booking API — writes to RDS, triggers SNS (admin) and SES (customer) emails
- **Data:** RDS MySQL (`staynest-db`)

---

## AWS Services Used

### Core
| Service | Resource | Purpose |
|---|---|---|
| EC2 | `cloudbnb-server` (t2.micro / t3.micro) | Nginx web server + Flask API |
| S3 | `cloudbnb-aazad-2026` | Property image storage |
| IAM | `staynest-dev` | Least-privilege read-only developer access |
| VPC | Default VPC, `172.31.0.0/16` | Network isolation, 6 subnets across AZs |
| RDS | `staynest-db` (MySQL, db.t4g.micro) | Booking data storage |

### Advanced
| Service | Resource | Purpose |
|---|---|---|
| CloudFront | `staynest-cdn` | Global CDN for property images (OAC-secured S3 origin) |
| CloudWatch | `staynest-cpu-alarm` | EC2 CPU monitoring, alarm at >80% |
| SNS | `staynest-bookings` topic | Owner notifications (alarms + new bookings) |
| SES | Verified sender identity | Automated customer booking confirmation emails |
| ALB + Auto Scaling Group | `staynest-asg-1` / `staynest-asg` | Load balancing + elastic scaling (1–3 instances) |

---

## Security

- **IAM least privilege:** dev user has read-only access to S3/RDS/CloudWatch only — no write/delete.
- **S3 bucket policy** (not ACLs) grants public `GetObject` read access, per current AWS guidance.
- **VPC isolation:** only port 80 open on EC2; RDS only accepts traffic from the EC2 security group.
- **CloudFront OAC** — CloudFront, not the public, is the only thing that talks to S3 directly.
- **No hardcoded credentials** — all AWS access via IAM roles/policies.
- Admin dashboard is password-protected (credential kept out of this repo — see `.env.example`).

---

## Cost

Every service was kept inside AWS Free Tier limits — **$0.00/month** during development:

| Service | Tier |
|---|---|
| EC2 | Free tier, 750 hrs/mo |
| S3 | Free tier, 5GB + 20K GET |
| RDS | Free tier, 750 hrs/mo |
| CloudFront | Free tier, 1TB/mo |
| CloudWatch | Free tier, 10 metrics/alarms |
| SNS | Free tier, 1M requests/mo |
| WAF | Disabled (avoided $14/mo charge) |

---

## Challenges & Debugging

A few real issues hit during deployment (full write-ups in the original report):

1. **`/admin` returning 404** — Nginx's `try_files` looked for a literal file named `admin`, not `admin.html`. Fixed with an explicit `location = /admin` block.
2. **Dashboard showing 0 bookings** — SQL query referenced a column (`booked_at`) that didn't exist; the actual column was `created_at`. Fixed in both the Flask query and the frontend JS.
3. **`TypeError: b.id.substring is not a function`** — booking IDs were numeric, but the frontend called `.substring()` assuming UUID strings. Fixed by coercing to `String(b.id)` first.
4. Debugged using `curl` against the Flask API directly (isolating backend vs. frontend issues) and browser DevTools Network/Console tabs.

---

## Repo contents

```
/app                # Flask booking API (booking_api.py)
/frontend            # Static HTML/CSS/JS site + admin.html
/nginx               # Nginx site config (location blocks for /admin, static routing)
/screenshots          # Console + live-site screenshots from deployment
/docs                # Full original project report (PDF)
.env.example          # Required environment variables (no real secrets)
```

---

## Tech Stack

`AWS (EC2, S3, RDS, IAM, VPC, CloudFront, CloudWatch, SNS, SES, ALB, ASG)` · `Nginx` · `Python / Flask` · `MySQL` · `boto3` · `HTML/CSS/JS`

---

## Author

Aazad Kumar Mishra
