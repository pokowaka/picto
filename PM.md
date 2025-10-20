## **Project: "Pictogram Task Sequencer"**

## **Document Version: 1.4**

### 1. 🎯 Vision & Problem Statement

* **Vision:** To act as an intelligent partner for caregivers, teachers, and therapists, dramatically reducing the time it takes to create visual schedules by translating **high-level goals** (not just explicit steps) into clear, editable, and accurate pictogram sequences.
* **Problem:** Creating visual schedules is a manual, time-consuming process of *both* planning the steps *and* finding the icons. This creates a high-friction barrier for busy caregivers.
* **Solution:** A hybrid-AI application that:
    1. Uses a generative **"Planner" (LLM)** to brainstorm a logical sequence of steps from a simple, high-level goal.
    2. Uses a deterministic **"Retriever" (SBERT)** to find the correct, corresponding pictograms for each step from our database.
    3. Presents this as an **editable template** for the Creator to quickly approve or "curate."

---

### 2. 👥 Functional Roles

* **The Creator:** The user (e.g., therapist, parent, teacher) responsible for inputting a high-level goal and "curating" (editing/approving) the AI-suggested sequence.
* **The End-User:** The user (e.g., individual with a cognitive disability) who consumes the final, Creator-approved pictogram sequence.

---

### 3. ✅ V1.0 (MVP) Scope & Core Hypothesis

This V1.0 tests the full "creative partner" loop, from goal to editable draft.

* **Core V1.0 Hypothesis:** A hybrid AI model (LLM Planner + SBERT Retriever) can generate a *useful, editable draft* of a task sequence from a high-level, natural language goal.
* **Definition of "Useful":** > 80% of the AI-suggested steps are relevant to the goal (even if they require re-ordering or minor replacement), and the Creator can finalize a routine *faster* than starting from a blank canvas.
* **V1.0 Functional Scope:**
    1. **Creator UI (Input):** A single text input field for a *high-level goal* (e.g., "Get ready for school," "Wash the dog").
    2. **Hybrid Engine:** The system executes the two-stage pipeline (LLM-Planner -> SBERT-Retriever).
    3. **Creator UI (Output):** An **editable sequence editor** that displays the AI-generated routine.
    4. **Curator Controls:** The Creator **must** be able to:
        * Drag-and-drop to **re-order** steps.
        * **Delete** suggested steps.
        * **Replace** a pictogram by clicking it, which reveals the Top-3 alternatives from the Retriever.
    5. **Save:** A "Save" button to finalize the curated routine.
* **EXPLICITLY OUT OF V1.0 SCOPE:**
  * A manual "search-from-scratch" interface.
  * End-User "Viewer" mode.

---

### 4. ⚙️ V1.0 System Architecture (Hybrid Model)

The V1.0 system is a three-stage pipeline.

#### 4.1. Stage 1: The "Planner" (Generative LLM)

* **Technology:** **`gemini-2.5-pro-latest`** (via Google AI Studio / Vertex AI API).
* **Rationale:** This model demonstrates strong performance in instruction-following, logical reasoning, and, critically, reliable JSON-formatted output.
* **Task:** Receives the Creator's high-level goal (e.g., "Help my son get to school in the morning").
* **Prompt (Internal):** The full V1 system prompt is specified in **Appendix B**. It instructs the LLM to act as a special needs education expert, break the goal into 5-7 steps, and generate a short `search_query` for each.
* **Output:** A structured JSON object.

**Example JSON Output:**

```json
{
  "routine_name": "Get Ready for School",
  "steps": [
    { "step_name": "Wake Up", "search_query": "wake up in bed" },
    { "step_name": "Get Dressed", "search_query": "put on clothes" },
    { "step_name": "Eat Breakfast", "search_query": "eat breakfast" },
    { "step_name": "Brush Teeth", "search_query": "brushing teeth" },
    { "step_name": "Get Backpack", "search_query": "school backpack" },
    { "step_name": "Put on Shoes", "search_query": "put on shoes" }
  ]
}
```

##### 4.1.1. Operational Analysis (Cost & Latency)

* **Pricing Tier:** The combined system prompt (Appendix A, ~1k tokens) and user goal (~20 tokens) is well under the 200,000-token threshold. We will therefore use the standard tier.
* **Cost Analysis (Per-Query):**
  * **Assumption:** Prices are per 1,000,000 tokens (M-tokens).
  * **Input (Estimate):** ~1,000 tokens (0.001 M-tokens) @ $1.25 / M-token = **$0.00125**
  * **Output (Estimate):** ~200 tokens (0.0002 M-tokens) @ $10.00 / M-token = **$0.00200**
  * **Total Cost Per Query:** **~$0.00325**
* **Cost Target (V1.0):** The V1.0 validation budget for 10,000 test generations is:
  * 10,000 generations * $0.00325/generation = **$32.50**
* **Latency Target:** The Planner (Stage 1) P95 latency must be **< 5.0 seconds**. This is well within the generous 90-second `Time to Curated Routine` (TCR) metric.
* **Key Benefits of this Model:**
  * **Cost-Effectiveness:** The V1.0 validation is extremely inexpensive ($32.50).
  * **Data Privacy:** The pricing scheme guarantees an option to prevent user data from being used for model improvement, a key feature for handling potentially sensitive user information.
  * **Future Optimization:** Context Caching ($0.125 / M-token) can be used for the static system prompt in V1.1, further reducing the per-query input cost.

#### 4.2. Stage 2: The "Retriever" (Deterministic SBERT)

* **Task:** Receives the `search_query` strings from the LLM's JSON output.
* **Technology:** A Sentence-BERT (SBERT) model (`all-mpnet-base-v2`).
* **Vector Database:** `ChromaDB`.
* **Process:** For each `search_query`, the Retriever performs a $k$-Nearest Neighbor search ($k=3$) against the `ChromaDB` index.

#### 4.3. Stage 3: The "Curator" (Creator UI)

* **Task:** The UI receives the `step_name` from Stage 1 and the Top 3 pictogram IDs from Stage 2.
* **Display:** The UI displays the `step_name` (e.g., "Get Dressed") with the **Top-1** matching pictogram.
* **Interaction:** When the Creator clicks a step to "Replace" it, the UI presents the **Top-2** and **Top-3** pictograms as simple, one-click alternatives.

#### 4.4. Pipeline Error Handling (Failure Path)

The system must be robust to failure in each stage.

* **Stage 1 (Planner) Failure:**
  * **Error:** LLM API returns a non-200 status code (e.g., 503, 429).
  * **Logic:** Implement an exponential backoff retry (3 attempts).
  * **UI Feedback:** If retries fail, display a modal: "Error: The AI Planner is unavailable. Please try again in a moment."
* **Stage 1 (Planner) Malformed Data:**
  * **Error:** LLM returns a 200 OK but the response is not valid JSON.
  * **Logic:** The application JSON parser fails. The system will *not* retry (to avoid a deterministic failure loop).
  * **UI Feedback:** Display a modal: "Error: The AI Planner returned a malformed response. We are working on it. Please try a different goal." (Log the malformed response for engineering review.)
* **Stage 2 (Retriever) Failure:**
  * **Error:** A `search_query` from the LLM yields zero relevant results from SBERT/ChromaDB (i.e., the Top-1 result has a similarity score below a pre-defined threshold, e.g., 0.3).
  * **Logic:** Do not fail the entire sequence.
  * **UI Feedback:** The UI will render the `step_name` (e.g., "Glargle the Flanz") with a "missing pictogram" placeholder (e.g., a query-mark icon). This makes the failure *visible and editable* by the Creator, who can then delete the step.

---

### 5. 🗃️ V1.0 Data Schema

```json
{
  "id": "picto_1024",
  "image_path": "img/nl/op_tijd_klaar_staan_kruis_rood.png",
  "concept_nl": "Te laat zijn (negatief)",
  "description_nl": "De afbeelding contrasteert op tijd klaarstaan met haasten omdat men te laat is, aangeduid met een rood kruis.",
  "tags_nl": [
    "op tijd",
    "klaarstaan",
    "wachten",
    "te laat",
    "haasten",
    "tijdmanagement",
    "afspraak",
    "rood kruis",
    "nee",
    "fout"
  ],
  "synonyms_nl": [
    "je bent te laat",
    "snel doen",
    "haast je"
  ],
  "categories": ["tijd", "gevoel", "abstract", "negatief"]
}
```

---

### 6. 📈 V1.0 Falsifiable Success Metrics

1. **Metric:** **Plan Usefulness Rate (PUR)**
    * **Definition:** The percentage of generated plans where the Creator does *not* need to manually add a new step.
    * **Target:** **PUR > 70%**

2. **Metric:** **Time to Curated Routine (TCR)**
    * **Definition:** The median time from a Creator submitting a high-level goal to them hitting "Save."
    * **Target:** **TCR < 90 seconds**

3. **Metric:** **Retriever Hit Rate (RHR)**
    * **Definition:** The percentage of LLM-generated `search_query` strings that produce a *relevant* pictogram (as judged by a human panel) in the Top-3 SBERT results.
    * **Target:** **RHR > 85%**

---

### Appendix A: Technical Glossary

This section explains the technical terms used in this document for non-expert stakeholders.

* **LLM (Large Language Model):** This is the "Planner" in our system. Think of it as a highly advanced AI with a vast "common sense" knowledge of the world. We give it a high-level goal (like "get ready for school"), and it *generates* a logical list of steps based on its understanding of that goal.
  * **Specified Model:** `gemini-2.5-pro-latest` is Google's specific, high-performance LLM that we will use for this task.

* **SBERT (Sentence-BERT):** This is the "Retriever" in our system. It's a specialized AI model that is excellent at one thing: understanding the *semantic meaning* of a sentence. It converts any text string (like "brushing teeth") into a list of numbers called a **vector**.

* **Vector (or Embedding):** A vector is a mathematical representation of meaning. Sentences with similar meanings will have similar vectors. For example, the vector for "put on coat" will be mathematically very close to the vector for "wear jacket," but very far from the vector for "eat breakfast."

* **ChromaDB:** This is our "Vector Database." It's a modern, open-source embedding database that stores the vectors for *every single pictogram* in our database and allows for very fast and efficient searching.

* **Vector Search (or Semantic Search):** This is the core process of the "Retriever."
    1. The LLM gives us a `search_query` (e.g., "put on clothes").
    2. SBERT turns this query into a **query vector**.
    3. We use `ChromaDB` to instantly compare this **query vector** against all the pictogram vectors in our database.
    4. `ChromaDB` returns the Top 3 pictograms whose vectors are mathematically *closest* in meaning to the query vector. This is how we find the "put on clothes" pictogram without the LLM needing to know it exists.

* **Hybrid Model:** Our term for combining the "Planner" (LLM) and the "Retriever" (SBERT/ChromaDB). The LLM *plans* the steps, and the Retriever *finds* the matching items. This gives us the common sense of an LLM while ensuring the results are deterministic and grounded in our actual database.

* **P95 Latency:** A performance metric. It means that 95% of all requests must be *faster* than the target time. A P95 latency of < 5.0 seconds means 95 out of 100 users will get a response in under 5 seconds, which is a strong measure of reliability.

* **JSON (JavaScript Object Notation):** A simple, text-based data format that is very easy for computers to read and write. It's how we command our LLM to return data in a perfectly structured way that our application can instantly understand, with no ambiguity.

### Appendix B: V1.0 Planner System Prompt

This text will be sent to the `gemini-2.5-pro-latest` model as the system prompt.

> You are an expert AI assistant specializing in special needs education and augmentative and alternative communication (AAC). You are assisting a caregiver (a parent, teacher, or therapist) who needs to quickly create a visual pictogram schedule.
>
> The user will provide a high-level, abstract goal in Dutch.
>
> Your task is to:
>
> 1. Analyze the user's goal.
> 2. Break this goal down into a simple, logical, and linear sequence of 5-7 concrete, actionable steps that an individual with a cognitive disability could follow.
> 3. The steps must be in the correct logical order (e.g., "put on socks" comes *before* "put on shoes").
> 4. For each step, create a very short `step_name` (in Dutch, max 3 words) that describes the action.
> 5. For each step, create a `search_query` (in Dutch) that will be used by a vector search engine to find a matching pictogram. This `search_query` should be descriptive (e.g., "tanden poetsen met tandenborstel," "ontbijt eten aan tafel").
>
> **CONSTRAINTS:**
>
> * You MUST respond *only* with a valid JSON object.
> * Do not include any text, pleasantries, or explanations before or after the JSON block.
> * The JSON must adhere to the following schema:
>
> ```json
> {
>   "routine_name": "string (A Dutch title for the routine)",
>   "steps": [
>     {
>       "step_name": "string (e.g., 'Aankleden')",
>       "search_query": "string (e.g., 'kleren aandoen')"
>     },
>     ...
>   ]
> }
> ```
>
> **EXAMPLE:**
> **User Goal:** "Help mijn zoon 's ochtends klaar te maken voor school"
> **Your Response:**
>
> ```json
> {
>   "routine_name": "Klaarmaken voor School",
>   "steps": [
>     {
>       "step_name": "Wakker worden",
>       "search_query": "wakker worden in bed"
>     },
>     {
>       "step_name": "Aankleden",
>       "search_query": "kleren aandoen"
>     },
>     {
>       "step_name": "Ontbijt eten",
>       "search_query": "ontbijt eten aan tafel"
>     },
>     {
>       "step_name": "Tanden poetsen",
>       "search_query": "tanden poetsen met tandenborstel"
>     },
>     {
>       "step_name": "Tas pakken",
>       "search_query": "rugzak of schooltas pakken"
>     },
>     {
>       "step_name": "Schoenen aan",
>       "search_query": "schoenen aandoen"
>     },
>     {
>       "step_name": "Jas aan",
>       "search_query": "jas aandoen"
>     }
>   ]
> }
> ```
>
> You are now ready to receive the user's goal. Respond ONLY with the JSON object.
