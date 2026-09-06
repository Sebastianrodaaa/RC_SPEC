**RC Investment: Offering Memorandum Generation POC**

**Owner:** Mark Bakshiyev, Pulse Foundry

**Client contacts:** Michael and Bradley, RC Investment Properties

**Trial deal:** Urbana, Phoenix AZ

**Status:** Draft, 3 September 2026

# **1\. Objective**

Build an AI skill that reads a Google Drive folder of deal materials and produces a 5 to 6 slide investor-facing Offering Memorandum in RC Investment's standard format.

The Midtown Grove OM is the template. The Urbana deal is the trial input.

Two things go to RC Investment: the finished Urbana deck, and the skill itself so they can rerun it on future deals.

# **2\. Why this matters to the client**

RC Investment analyzes hundreds of deals a year and closes 2 to 4\. They pay roughly $2,500 per OM today, and the process is manual and inconsistent. Location and market content is the piece they find hardest to produce.

This is a fixed-scope test before any retainer discussion. Output quality and repeatability are what they will judge.

# **3\. Inputs**

All source material lives in one shared Google Drive folder. The skill must work from the folder contents alone, without hardcoding anything because exact material format may vary in real world situations.

| Input | Source | Used for |
| :---- | :---- | :---- |
| Midtown Grove OM | RC Investment | Format, section order, tone, layout reference |
| Broker package (Urbana) | Seller's broker | Asset summary, property specs, some market content |
| Excel underwriting model (Urbana) | RC Investment | Rent roll, trailing 12 income statement, budget summary |
| Asset and area photos | Bradley and Michael, via CoStar or broker | Photo placement throughout |
| Market research, if present | Broker package or market reports | Location and market slide |

Do not expand beyond these inputs. Live market research was considered as a third input and then dropped, to keep the research burden down. If the broker package is missing a market stat, leave a clearly marked placeholder. Do not fabricate a number.

# **4\. Output: slide by slide**

Format follows Midtown Grove: bullets rather than paragraphs, photos throughout, RC Investment branding.

## **Slide 1\. Asset summary**

* Unit count, year built, property type, address

* Basic physical specs such as plumbing and roof, where available

* Source: broker package. Include one or two asset photos

## **Slide 2\. Rent roll**

* Four columns only: unit type, size in square feet, in-place rent, market rent

* Aggregate by unit type. No unit-by-unit listing

* Source: Excel model

## **Slide 3\. Income statement**

* Fixed line items from the trailing 12: marketing, repairs and maintenance, admin, utilities, plus totals

* Match the line item order used in Midtown Grove

* Source: Excel model

## **Slide 4\. Budget**

* Full-year budget picture

* Current practice is a screenshot of the Excel summary page. For the POC, reproduce that or render the same figures as a native table

* Source: Excel model

## **Slide 5\. Location and market**

* Why invest in Phoenix, neighborhood description, headline market stats such as unemployment rate and household growth

* Bullet form

* Source: broker package first, then any market report in the folder. Include area photos

## **Slide 6\. Photos, optional**

* Additional asset and area photos if there are enough to justify a standalone page

* Otherwise fold them into slides 1 and 5

# **5\. Success criteria**

The POC passes when all four hold:

1. The skill generates the Urbana deck from the Drive folder with no manual edits to content.

2. It does so on 2 to 3 consecutive runs with consistent structure and consistent numbers.

3. Every figure traces back to a specific cell or page in the source material. No invented data.

4. The format is close enough to Midtown Grove that Michael and Bradley recognize it as theirs.

Nothing goes to RC Investment until all four are met internally.

# **6\. Out of scope**

* Investor engagement content such as monthly or quarterly outreach and macro commentary. Separate use case, later phase

* Full 10 page OMs. The trial is 5 to 6 slides

* Sourcing market data from the open web. Use what is in the folder

* Pixel-perfect brand fidelity. Structure and content first, polish after the flow works

# **7\. Build approach**

1. **Document the template.** Read the Midtown Grove OM and write down the exact section order, headers, and per-section content pattern. This becomes the skill's format guide.

2. **Map output to source.** For each slide, record which Excel sheet and range, or which broker package page, it comes from. This mapping is the core of the skill.

3. **Build extraction first.** Parse the Excel and PDF inputs before touching deck generation. Verify extracted numbers against the source by hand.

4. **Generate the deck.** Compare against Midtown Grove side by side.

5. **Test repeatability.** Run it 2 to 3 times from a clean state and diff the outputs.

6. **Package it.** Ship the skill with a short README so RC Investment can point it at a new folder.