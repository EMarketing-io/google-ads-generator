import json
import time
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

prompt_template = PromptTemplate(
    input_variables=["rules", "company", "offers", "keywords"],
    template="""
You are a Google Ads strategist.

🎯 TASK:
Generate a high-converting Responsive Search Ad for a service using the provided TRAINING RULES, COMPANY INFO, OFFERS, and KEYWORDS.

✅ Your ad must include:
- A meaningful ad group name based on keyword theme (not "Group 1")
- 10 diverse and creative headlines (max 30 chars, avoid repeated words)
- 4 full, grammatically correct descriptions (max 90 chars)

💡 Headlines should:
- Highlight different features, offers, benefits, or actions
- Avoid repeating any word more than once
- Use emotion, value, and specificity

# TRAINING RULES:
{rules}

# COMPANY INFO:
{company}

# CURRENT OFFERS:
{offers}

# KEYWORDS:
{keywords}

Return only valid JSON:
{{
  "adGroupName": "<<< generated >>>",
  "path1": "...",
  "path2": "...",
  "headlines": ["..."],
  "descriptions": ["..."]
}}
""",
)


def generate_ads(llm, keyword_groups, rules, company, offers):
    chain = LLMChain(llm=llm, prompt=prompt_template)
    ads = []

    for idx, (label, keywords) in enumerate(keyword_groups.items()):
        print(
            f"\n📢 [{idx+1}/{len(keyword_groups)}] Generating ad for keyword group: '{label}'"
        )
        try:
            response = chain.run(
                rules=rules,
                company=company,
                offers=offers,
                keywords=", ".join(keywords),
            )
            ad = json.loads(response.strip("```json\n").strip("```").strip())
            unique_headlines = list(dict.fromkeys(ad["headlines"]))[:10]
            unique_descriptions = list(dict.fromkeys(ad["descriptions"]))[:4]

            ads.append(
                {
                    "Campaign": "emarketing",
                    "Ad group": ad.get("adGroupName", f"AdGroup_{idx+1}"),
                    "Ad type": "Responsive Search Ad",
                    "Final URL": "",
                    "Path 1": ad.get("path1", ""),
                    "Path 2": ad.get("path2", ""),
                    **{
                        f"Headline {i+1}": (
                            unique_headlines[i] if i < len(unique_headlines) else ""
                        )
                        for i in range(10)
                    },
                    **{
                        f"Description {i+1}": (
                            unique_descriptions[i]
                            if i < len(unique_descriptions)
                            else ""
                        )
                        for i in range(4)
                    },
                }
            )
        except Exception as e:
            print(f"❌ Error for group '{label}': {e}")
        time.sleep(1)

    return ads
