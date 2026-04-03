# GhostGrid — Taxonomy Schema

> **Purpose:** This document defines the label categories used by our data labeling team to classify messages scraped from informal trade channels (Telegram groups, OLX listings, etc.). Consistent application of these labels is critical for training our NLP classifier.

---

## Label Categories

| Label | Description |
|---|---|
| `shortage_signal` | Indicates scarcity, stockouts, or supply shortfall |
| `price_hike` | Indicates abnormal price increases or inflation signals |
| `urgency_sale` | Indicates panic selling, liquidation, or time-pressured offers |
| `neutral` | General trade chatter with no actionable market signal |

---

## 1. `shortage_signal`

**Definition:** A message that explicitly or implicitly communicates a shortage, stockout, or difficulty in sourcing a particular good. Look for language around unavailability, empty stock, long wait times, or rationing.

### Examples

> **Example 1 (Telegram):**
> "Bro does anyone have 50kg cement bags left? Checked 4 warehouses in Jebel Ali, all sold out since last week. Factories aren't dispatching."

> **Example 2 (OLX):**
> "LOOKING TO BUY — 200 litres cooking oil (any brand). Cannot find stock anywhere in Deira market. Willing to pay above MRP. DM urgent."

---

## 2. `price_hike`

**Definition:** A message that signals an abnormal or sudden increase in the price of goods, whether through direct price quotes, complaints about rising costs, or comparisons to previous pricing. Look for language around price jumps, markups, and cost escalation.

### Examples

> **Example 1 (Telegram):**
> "Steel rebar rates just jumped 40% overnight. Last month was ₹52/kg, dealer is now quoting ₹73/kg. Something is going on with the supply chain."

> **Example 2 (OLX):**
> "Rice 25kg bag — AED 180 (was AED 110 two weeks ago). Price is firm, don't message asking for discount. Import costs have gone up."

---

## 3. `urgency_sale`

**Definition:** A message that indicates a seller is trying to offload goods quickly, often at a discount or under time pressure. This may signal panic selling, inventory liquidation, perishable stock nearing expiry, or forced clearance. Look for language around urgency, deadlines, bulk dumps, and steep discounts.

### Examples

> **Example 1 (Telegram):**
> "CLEARANCE — 5 tons of frozen chicken arriving tomorrow, must sell by Friday or it goes to waste. 30% below market. Pickup only from Al Quoz cold storage. First come first served."

> **Example 2 (OLX):**
> "Shutting down warehouse. 800 boxes of electronics accessories — cables, chargers, cases. Take everything for AED 3,000. Need gone by end of day Sunday. No single-piece sales."

---

## 4. `neutral`

**Definition:** A message that is general trade conversation, routine listings, casual inquiries, or social chatter with no clear signal of shortage, price abnormality, or urgency. These messages represent the baseline noise in informal trade channels.

### Examples

> **Example 1 (Telegram):**
> "Hey team, the new shipment from Guangzhou landed yesterday. Standard pricing, same terms as last order. Invoice will be shared by EOD."

> **Example 2 (OLX):**
> "For sale: Office furniture — 10 desks + chairs, lightly used. AED 150 per set. Located in Business Bay. Can deliver within Dubai for extra charge."

---

## Labeling Guidelines

1. **One label per message.** Choose the **strongest** signal present. If a message contains both a shortage signal and a price hike, label based on the **primary intent** of the message.
2. **When in doubt, label `neutral`.** Only apply a signal label when there is clear evidence in the text.
3. **Ignore emojis and slang** for classification purposes — focus on the semantic content.
4. **Context matters.** A high price alone is not a `price_hike`; there must be an indication that the price is *abnormally* elevated compared to a baseline.
5. **Flag edge cases** in the `notes` column of the labeling spreadsheet for team review.

---

## Annotation Format

Each labeled sample should include:

| Field | Type | Description |
|---|---|---|
| `message_id` | `string` | Unique identifier for the message |
| `source` | `string` | Channel source (`telegram`, `olx`, `other`) |
| `text` | `string` | Raw message text |
| `label` | `string` | One of: `shortage_signal`, `price_hike`, `urgency_sale`, `neutral` |
| `confidence` | `float` | Annotator confidence (0.0–1.0) |
| `notes` | `string` | Optional — edge case explanations or context |

---

*Last updated: 2026-04-03 • GhostGrid NLP Team*
