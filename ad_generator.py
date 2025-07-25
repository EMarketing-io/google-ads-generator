import json
import time
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

prompt_template = PromptTemplate(
    input_variables=["website", "questionnaire", "offers", "transcript", "keywords"],
    template="""
You are a Google Ads strategist.

🎯 TASK:
Generate a high-converting Responsive Search Ad using the provided TRAINING RULES, COMPANY INFO, OFFERS, and TARGET KEYWORDS.

✅ Return strictly valid JSON only. Do not include any commentary, explanations, markdown (like ```json), or extra formatting. The JSON should match the schema shown at the bottom.

💡 PRIORITIZATION:
- Emphasize emotion, urgency, clarity, and user benefit.
- Focus on outcomes (“Save time” vs. “Fast delivery”) and value (“Free Trial” vs. “We offer services”).
- Match tone and voice based on the COMPANY INFO provided (e.g., formal, playful, premium, budget-friendly).
- Do not repeat words or phrases across ad elements unless absolutely necessary.
- ❌ Do not mention or imply competitors (e.g., avoid phrases like “better than”, “upgrade from”, or comparisons like “X vs Y”).
- ✅ Focus only on the strengths and benefits of the advertised product or brand.

---

🧱 JSON FIELDS TO RETURN:

1. Ad Group Metadata
- `adGroupName`: Short, keyword-relevant group name (not generic like “Group 1”)
- `path1`, `path2`: Optional slugs to enhance display URL

2. Headlines
- `headlines`: 10 unique, attention-grabbing lines (max 30 characters each)
  - Each headline should showcase a different benefit, action, or emotional trigger
  - Avoid repeated phrasing across headlines

3. Descriptions
- `descriptions`: 4 distinct descriptions (max 90 characters)
  - Be clear, concise, and emotionally persuasive
  - Focus on urgency or user reward

4. Callouts
- `callouts`: 8 short promotional phrases (max 25 characters each)
  - Highlight perks like Free Delivery, 24/7 Service, Top Rated, etc.
  - Avoid repetition or punctuation unless necessary for clarity

💡 Callout Extension Best Practices:
- Don’t make your callouts too repetitive — each one should convey a different value.
- Since callouts appear near your descriptions, avoid overlapping content to prevent audience fatigue.
  
5. Sitelinks
- `sitelinks`: 4 sitelinks
  - Each must include:
    - `headline`: Short title (max 25 characters)
    - `description1`: Supporting sentence (max 35 characters)
    - `description2`: Secondary elaboration (max 35 characters)
  - Each sitelink must be clearly distinct

💡 Structured Snippet Best Practices:
- Make sure your structured snippets clearly convey what you’re offering.
- Instead of vague terms like “bundles available,” list the actual contents (e.g., “Free T-Shirt, 30-Day Trial”).
- Each value should be distinct and concrete.  

6. Structured Snippet
- `structuredSnippet`:
  - `snippetType`: Choose the most relevant type from this list:
    Amenities, Brand, Courses, Degree Programs, Destinations, Featured Hotels, Insurance Coverage, Models, Neighbourhood, Service Catalogue, Shows, Styles, Types
  - `values`: 4 snippet values (max 25 characters each, all unique)

💡 Structured Snippet Best Practices:
- Make sure your structured snippets clearly convey what you’re offering.
- Instead of vague terms like “bundles available,” list out specific items in the bundle.
- Each value should be distinct and tangible.

7. Extensions
- `callExtension`: One strong call-based CTA (max 25 characters)
- `locationExtension`: Address, area served, or city name (no length limit)
- `promotionalExtension`: Urgent discount/promo line (max 25 characters)
- `priceExtension`: Pricing/value phrase (max 25 characters)

💡 Call Extension Best Practices:
- Ensure your team is ready to answer calls. Set up tracking if needed.

💡 Location Extension Best Practices:
- Double-check location relevance. Update if your ads target different areas.

💡 Promotional Extension Best Practices:
- Always use start/end dates. Avoid outdated promos.

💡 Price Extension Best Practices:
- Don’t include seasonal prices unless they’re regularly updated.
- Only promote prices that are truly valid site-wide.

---

📄 WEBSITE SUMMARY:
Use this to define brand voice, tone, values, and high-level messaging:
{website}

---

📋 QUESTIONNAIRE:
Use this to understand features, product info, and user pain points:
{questionnaire}

---

🎁 OFFERS:
Incorporate promotions, guarantees, or special features:
{offers}

---

🎙️ AUDIO TRANSCRIPT (e.g. Zoom):
Use this to capture intent, delivery style, and customer phrasing:
{transcript}

---

🔑 TARGET KEYWORDS:
These are the only themes or search intents this ad should be focused on. Do not drift to unrelated topics:
{keywords}

---

✍ Return JSON like this:

{{
  "adGroupName": "...",
  "path1": "...",
  "path2": "...",
  "headlines": ["...", "..."],
  "descriptions": ["...", "..."],
  "callouts": ["...", "..."],
  "sitelinks": [
    {{
      "headline": "...",
      "description1": "...",
      "description2": "..."
    }},
    ...
  ],
  "structuredSnippet": {{
    "snippetType": "Models",
    "values": ["...", "...", "...", "..."]
  }},
  "callExtension": "...",
  "locationExtension": "...",
  "promotionalExtension": "...",
  "priceExtension": "..."
}}
""",
)


def generate_ads(
    llm, keyword_groups, website, questionnaire="", offers="", transcript=""
):
    chain = LLMChain(llm=llm, prompt=prompt_template)
    ads = []

    for idx, (label, keywords) in enumerate(keyword_groups.items()):
        if not any(keywords):
            continue

        print(
            f"\n📢 [{idx+1}/{len(keyword_groups)}] Generating ad for keyword group: '{label}'"
        )

        try:
            response = chain.run(
                website=website,
                questionnaire=questionnaire,
                offers=offers,
                transcript=transcript,
                keywords=", ".join(keywords),
            )
            ad = json.loads(response.strip("```json\n").strip("```").strip())

            # Clean and deduplicate content
            def clean_list(items, max_len):
                seen = set()
                result = []
                for item in items:
                    item = item.strip()
                    if item and item not in seen:
                        seen.add(item)
                        result.append(item)
                    if len(result) >= max_len:
                        break
                return result

            headlines = clean_list(ad.get("headlines", []), 10)
            descriptions = clean_list(ad.get("descriptions", []), 4)
            callouts = clean_list(ad.get("callouts", []), 8)
            snippets = clean_list(ad.get("structuredSnippet", {}).get("values", []), 4)
            sitelinks = ad.get("sitelinks", [])[:4]
            snippet_type = ad.get("structuredSnippet", {}).get("snippetType", "")

            # Build the final ad row
            ad_row = {
                "Campaign": "emarketing",
                "Ad group": ad.get("adGroupName", f"AdGroup_{idx+1}"),
                "Ad type": "Responsive Search Ad",
                "Final URL": "",
                "Path 1": ad.get("path1", "").strip(),
                "Path 2": ad.get("path2", "").strip(),
                **{
                    f"Headline {i+1}": (headlines[i] if i < len(headlines) else "")
                    for i in range(10)
                },
                **{
                    f"Description {i+1}": (
                        descriptions[i] if i < len(descriptions) else ""
                    )
                    for i in range(4)
                },
                **{
                    f"Callout {i+1}": (callouts[i] if i < len(callouts) else "")
                    for i in range(8)
                },
            }

            for i in range(4):
                sl = sitelinks[i] if i < len(sitelinks) else {}
                ad_row[f"Sitelink Headline {i+1}"] = sl.get("headline", "").strip()
                ad_row[f"Sitelink Description {i*2+1}"] = sl.get(
                    "description1", ""
                ).strip()
                ad_row[f"Sitelink Description {i*2+2}"] = sl.get(
                    "description2", ""
                ).strip()

            # Add structured snippet
            ad_row["Structured Snippets Type"] = snippet_type.strip()
            for i in range(4):
                ad_row[f"Structured Snippets {i+1}"] = (
                    snippets[i] if i < len(snippets) else ""
                )

            # Add extensions
            ad_row["Call Extension"] = ad.get("callExtension", "").strip()
            ad_row["Location Extension"] = ad.get("locationExtension", "").strip()
            ad_row["Promotional Extension"] = ad.get("promotionalExtension", "").strip()
            ad_row["Price Extension"] = ad.get("priceExtension", "").strip()

            ads.append(ad_row)

        except Exception as e:
            print(f"❌ Error for group '{label}': {e}")
        time.sleep(1)

    return ads
