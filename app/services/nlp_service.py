"""NLP service for legal document entity extraction.

Implements comprehensive legal NER using:
- Regex patterns for structured legal entities (dates, citations, statutes)
- spaCy NER for persons, organizations, locations
- Domain-specific extractors for court names, bench composition, parties
- Sliding window chunking for long documents
"""
import logging
import re
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class NLPEntity:
    """Extracted named entity with confidence and mapping information."""
    entity_type: str
    text: str
    confidence: float
    token_start: int = 0
    token_end: int = 0
    source_chunk_idx: int = 0


class NLPService:
    """Legal document Named Entity Recognition service.

    Uses a hybrid approach combining:
    1. Regex patterns for structured legal entities
    2. Keyword-based extraction for courts, acts, sections
    3. spaCy (if available) for general NER
    """

    # Comprehensive Indian legal entity patterns
    LEGAL_PATTERNS = {
        "COURT": [
            r"(?:Supreme\s+Court\s+of\s+India)",
            r"(?:High\s+Court\s+of\s+[\w\s]+?)(?=\s+at|\s+bench|\s*[,\.\n])",
            r"(?:High\s+Court\s+at\s+\w+)",
            r"(?:District\s+(?:and\s+Sessions\s+)?Court[\w\s,]*)",
            r"(?:National\s+(?:Green\s+)?Tribunal[\w\s,]*)",
            r"(?:National\s+Company\s+Law\s+(?:Tribunal|Appellate\s+Tribunal))",
            r"(?:Consumer\s+(?:Disputes?\s+Redressal\s+)?(?:Forum|Commission)[\w\s,]*)",
            r"(?:Central\s+Administrative\s+Tribunal)",
            r"(?:Income\s+Tax\s+Appellate\s+Tribunal)",
            r"(?:Tribunal[\w\s,]*)",
        ],
        "JUDGE": [
            r"(?:(?:Hon['']?ble|Honourable)\s+(?:(?:Mr|Mrs|Ms|Justice|Chief\s+Justice|Dr)[.\s]+)*(?:Justice\s+)?[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
            r"(?:Justice\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
            r"(?:Chief\s+Justice\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
            r"(?:(?:J\.|JJ\.)\s*$)",
        ],
        "STATUTE": [
            r"(?:(?:The\s+)?(?:Indian\s+)?(?:Penal\s+Code|Contract\s+Act|Evidence\s+Act|Limitation\s+Act|Constitution\s+of\s+India|"
            r"Code\s+of\s+Criminal\s+Procedure|Code\s+of\s+Civil\s+Procedure|"
            r"Right\s+to\s+Information\s+Act|Companies\s+Act|"
            r"Arbitration\s+and\s+Conciliation\s+Act|Motor\s+Vehicles\s+Act|"
            r"Consumer\s+Protection\s+Act|Negotiable\s+Instruments\s+Act|"
            r"Transfer\s+of\s+Property\s+Act|Registration\s+Act|"
            r"Specific\s+Relief\s+Act|Industrial\s+Disputes\s+Act|"
            r"Prevention\s+of\s+Corruption\s+Act|NDPS\s+Act|"
            r"Information\s+Technology\s+Act|Income\s+Tax\s+Act|"
            r"Goods\s+and\s+Services\s+Tax\s+Act|GST\s+Act|"
            r"Insolvency\s+and\s+Bankruptcy\s+Code|"
            r"Electricity\s+Act|Environment\s+Protection\s+Act|"
            r"Essential\s+Commodities\s+Act|Hindu\s+Marriage\s+Act|"
            r"Hindu\s+Succession\s+Act|Muslim\s+Personal\s+Law|"
            r"Protection\s+of\s+Women\s+from\s+Domestic\s+Violence\s+Act)(?:,?\s*\d{4})?)",
            r"(?:(?:Section|Sec\.?|S\.?)\s+\d+[A-Za-z]?(?:\s*(?:read\s+with|r/w|r\.w\.)\s+(?:Section|Sec\.?|S\.?)\s+\d+[A-Za-z]?)*)",
            r"(?:Article\s+\d+(?:\s*\(\d+\))?(?:\s*\([a-z]\))?(?:\s+of\s+the\s+Constitution)?)",
            r"(?:Order\s+[IVXLCDM]+(?:\s+Rule\s+\d+)?(?:\s+of\s+(?:CPC|Code\s+of\s+Civil\s+Procedure))?)",
            r"(?:Rule\s+\d+(?:\s*\([a-z]\))?)",
        ],
        "CASE_CITATION": [
            r"(?:\d{4}\s*\(\d+\)\s*(?:SCC|SCR|AIR|Bom\s*CR|Cal|Mad|Del|Kar)\s*\d+)",
            r"(?:AIR\s+\d{4}\s+(?:SC|Bom|Cal|Mad|Del|Kar|All|Pat|AP|Guj|HP|J&K|Ker|MP|Ori|P&H|Raj|Gau)\s+\d+)",
            r"(?:\(\d{4}\)\s+\d+\s+SCC\s+\d+)",
            r"(?:(?:W\.?P\.?|SLP|CRL\.?A\.?|C\.?A\.?|T\.?P\.?|O\.?A\.?)\s*\(?\s*(?:C|Crl|Civil|Criminal)?\s*\)?\s*(?:No\.?\s*)?\d+(?:\s*/\s*\d{4})?(?:\s+of\s+\d{4})?)",
            r"(?:Criminal\s+Appeal\s+No\.?\s*\d+(?:\s+of\s+\d{4})?)",
            r"(?:Civil\s+Appeal\s+No\.?\s*\d+(?:\s+of\s+\d{4})?)",
            r"(?:Writ\s+Petition\s*\(?\s*(?:C|Civil|Crl|Criminal)?\s*\)?\s*No\.?\s*\d+(?:\s+of\s+\d{4})?)",
        ],
        "DATE": [
            r"(?:\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July|August|September|October|November|December),?\s+\d{4})",
            r"(?:\d{1,2}[./-]\d{1,2}[./-]\d{2,4})",
            r"(?:(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})",
            r"(?:dated\s+\d{1,2}[./-]\d{1,2}[./-]\d{2,4})",
        ],
        "MONETARY_VALUE": [
            r"(?:Rs\.?\s*[\d,]+(?:\.\d+)?(?:\s*(?:crore|lakh|thousand|lac|cr|lacs|crores|lakhs)s?)?)",
            r"(?:₹\s*[\d,]+(?:\.\d+)?(?:\s*(?:crore|lakh|thousand|lac|cr|lacs|crores|lakhs)s?)?)",
            r"(?:INR\s*[\d,]+(?:\.\d+)?)",
            r"(?:\d+(?:,\d{2,3})*(?:\.\d+)?\s*(?:crore|lakh|thousand|lac|cr|lacs|crores|lakhs)s?)",
        ],
        "LEGAL_TERM": [
            r"(?:(?:habeas\s+corpus|mandamus|certiorari|quo\s+warranto|prohibition))",
            r"(?:(?:prima\s+facie|res\s+judicata|sub\s+judice|mala\s+fide|bona\s+fide|inter\s+alia|ultra\s+vires|suo\s+motu))",
            r"(?:(?:injunction|stay\s+order|bail|anticipatory\s+bail|quash(?:ing|ed)?))",
            r"(?:(?:FIR|charge\s*sheet|chargesheet|complaint|plaint|written\s+statement))",
        ],
        "PARTY": [
            r"(?:(?:Petitioner|Respondent|Appellant|Defendant|Plaintiff|Complainant|Accused|Applicant|Opposite\s+Party)(?:\s*(?:No\.?\s*\d+))?)",
        ],
        "ORGANIZATION": [
            r"(?:(?:Union|State|Government)\s+of\s+(?:India|[\w\s]+))",
            r"(?:(?:Central|State)\s+(?:Government|Bureau\s+of\s+Investigation|CBI))",
            r"(?:(?:Reserve\s+Bank\s+of\s+India|RBI|SEBI|TRAI|IRDAI|NCLT|NCLAT))",
            r"(?:(?:Municipality|Municipal\s+Corporation|Panchayat|Gram\s+Panchayat)[\w\s,]*)",
            r"(?:(?:University|Institute|College|Board|Authority|Commission|Committee)[\w\s]*)",
        ],
        "PROVISION": [
            r"(?:(?:clause|sub-clause|sub-section|proviso|explanation|schedule|annexure)\s*\(?(?:\d+|[a-z]|[ivx]+)\)?)",
        ],
        "DEADLINE": [
            r"(?:within\s+(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|thirty|sixty|ninety)\s+(?:days?|weeks?|months?|years?))",
            r"(?:(?:not\s+later\s+than|on\s+or\s+before|by|before)\s+\d{1,2}(?:st|nd|rd|th)?\s+\w+,?\s+\d{4})",
            r"(?:(?:time\s+limit|limitation\s+period)\s+of\s+\d+\s+(?:days?|months?|years?))",
        ],
    }

    def __init__(
        self,
        model_name: str = "law-ai/InLegalBERT",
        chunk_size: int = 400,
        chunk_overlap: int = 50,
        confidence_threshold: float = 0.75,
        device: Optional[str] = None,
    ):
        """Initialize NLP service.

        Args:
            model_name: HuggingFace model identifier (unused in hybrid mode)
            chunk_size: Character window size for text chunking
            chunk_overlap: Overlap between consecutive chunks
            confidence_threshold: Score below which requires_review is set True
            device: Device (unused in hybrid mode)
        """
        self.model_name = model_name
        self.chunk_size = chunk_size * 4  # Convert token size to approximate char size
        self.chunk_overlap = chunk_overlap * 4
        self.confidence_threshold = confidence_threshold

        # Try loading spaCy for supplemental NER
        self.nlp = None
        try:
            import spacy
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("spaCy en_core_web_sm loaded for supplemental NER")
        except Exception:
            logger.info("spaCy not available — using regex-only extraction")

        logger.info(f"NLPService initialized (hybrid legal NER mode)")

    def extract_entities_from_text(self, text: str) -> List[NLPEntity]:
        """Extract named entities from legal text using hybrid approach.

        Args:
            text: Raw text to process

        Returns:
            List of NLPEntity objects with confidence scores
        """
        all_entities: List[NLPEntity] = []

        # 1. Regex-based legal entity extraction (high confidence)
        for entity_type, patterns in self.LEGAL_PATTERNS.items():
            for pattern in patterns:
                try:
                    for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
                        entity_text = match.group(0).strip()
                        if len(entity_text) < 2 or len(entity_text) > 500:
                            continue

                        # Confidence based on match quality
                        conf = 0.92 if len(entity_text) > 5 else 0.78

                        entity = NLPEntity(
                            entity_type=entity_type,
                            text=entity_text,
                            confidence=conf,
                            token_start=match.start(),
                            token_end=match.end(),
                        )
                        all_entities.append(entity)
                except re.error as e:
                    logger.debug(f"Regex error for {entity_type}: {e}")
                    continue

        # 2. spaCy NER for persons, orgs, locations, dates (if available)
        if self.nlp:
            try:
                # Process in chunks to avoid memory issues
                for i in range(0, len(text), self.chunk_size):
                    chunk = text[i : i + self.chunk_size + self.chunk_overlap]
                    doc = self.nlp(chunk)
                    for ent in doc.ents:
                        if ent.label_ in ("PERSON", "ORG", "GPE", "LOC", "DATE", "MONEY", "LAW"):
                            mapped_type = {
                                "PERSON": "PERSON",
                                "ORG": "ORGANIZATION",
                                "GPE": "LOCATION",
                                "LOC": "LOCATION",
                                "DATE": "DATE",
                                "MONEY": "MONETARY_VALUE",
                                "LAW": "STATUTE",
                            }.get(ent.label_, ent.label_)

                            entity = NLPEntity(
                                entity_type=mapped_type,
                                text=ent.text.strip(),
                                confidence=0.82,
                                token_start=i + ent.start_char,
                                token_end=i + ent.end_char,
                            )
                            all_entities.append(entity)
            except Exception as e:
                logger.warning(f"spaCy NER failed: {e}")

        # 3. Extract petitioner vs respondent names from case caption
        caption_entities = self._extract_case_caption(text)
        all_entities.extend(caption_entities)

        # Deduplicate
        deduped = self._deduplicate_entities(all_entities)
        logger.info(f"Extracted {len(deduped)} unique entities ({len(all_entities)} raw)")
        return deduped

    def _extract_case_caption(self, text: str) -> List[NLPEntity]:
        """Extract petitioner and respondent names from case caption."""
        entities = []

        # Look for "X ... vs/versus/v. ... Y" pattern in first 2000 chars
        caption_text = text[:2000]
        vs_pattern = r"([A-Z][A-Za-z\s&.,]+?)\s+(?:Vs?\.?|versus|VERSUS)\s+([A-Z][A-Za-z\s&.,]+?)(?:\n|\r|$)"
        match = re.search(vs_pattern, caption_text)
        if match:
            petitioner = match.group(1).strip().rstrip(".,")
            respondent = match.group(2).strip().rstrip(".,")
            if 3 < len(petitioner) < 200:
                entities.append(NLPEntity(
                    entity_type="PETITIONER",
                    text=petitioner,
                    confidence=0.95,
                    token_start=match.start(1),
                    token_end=match.end(1),
                ))
            if 3 < len(respondent) < 200:
                entities.append(NLPEntity(
                    entity_type="RESPONDENT",
                    text=respondent,
                    confidence=0.95,
                    token_start=match.start(2),
                    token_end=match.end(2),
                ))

        return entities

    def _deduplicate_entities(self, entities: List[NLPEntity]) -> List[NLPEntity]:
        """Deduplicate overlapping entity mentions and keep highest confidence score."""
        if not entities:
            return []

        entity_groups: Dict[Tuple[str, str], List[NLPEntity]] = {}
        for entity in entities:
            # Normalize: lowercase and strip whitespace for dedup key
            key = (entity.entity_type, re.sub(r'\s+', ' ', entity.text.lower().strip()))
            if key not in entity_groups:
                entity_groups[key] = []
            entity_groups[key].append(entity)

        deduped = []
        for group_entities in entity_groups.values():
            best_entity = max(group_entities, key=lambda e: e.confidence)
            deduped.append(best_entity)

        # Sort by entity type, then confidence desc
        deduped.sort(key=lambda e: (e.entity_type, -e.confidence))
        return deduped

    def map_entities_to_coordinates(
        self,
        entities: List[NLPEntity],
        words_with_coords,  # List of ExtractedWord from PDFService
    ) -> List[Dict[str, Any]]:
        """Map NER entities to their bounding box coordinates from PDF extraction.

        Args:
            entities: NLP extracted entities
            words_with_coords: List of ExtractedWord objects from PDFService

        Returns:
            List of entity dicts with bounding_box_coords populated
        """
        mapped_entities = []

        for entity in entities:
            entity_dict = {
                "entity_type": entity.entity_type,
                "extracted_text": entity.text,
                "confidence_score": entity.confidence,
                "requires_review": entity.confidence < self.confidence_threshold,
                "bounding_box_coords": None,
            }

            # Find matching word(s) in coordinates
            bbox = self._find_entity_bbox(entity.text, words_with_coords)
            if bbox:
                entity_dict["bounding_box_coords"] = bbox

            mapped_entities.append(entity_dict)

        return mapped_entities

    def _find_entity_bbox(self, entity_text: str, words_with_coords) -> Optional[Dict[str, Any]]:
        """Find bounding box for entity by matching words."""
        entity_lower = entity_text.lower().strip()
        entity_words = entity_lower.split()
        if not entity_words:
            return None

        matched_words = []

        # Try to find the first word of the entity
        for i, word_obj in enumerate(words_with_coords):
            word_lower = word_obj.text.lower().strip()
            if entity_words[0] in word_lower or word_lower in entity_words[0]:
                # Check if subsequent words also match
                candidate_words = [word_obj]
                match_count = 1

                for j in range(1, min(len(entity_words), len(words_with_coords) - i)):
                    next_word = words_with_coords[i + j].text.lower().strip()
                    if j < len(entity_words) and (entity_words[j] in next_word or next_word in entity_words[j]):
                        candidate_words.append(words_with_coords[i + j])
                        match_count += 1

                # Accept if we matched at least half the words
                if match_count >= max(1, len(entity_words) // 2):
                    matched_words = candidate_words
                    break

        # Fallback: substring matching
        if not matched_words:
            for word_obj in words_with_coords:
                if entity_lower in word_obj.text.lower() or word_obj.text.lower() in entity_lower:
                    matched_words.append(word_obj)
                    break

        if not matched_words:
            return None

        first_word = matched_words[0]
        min_x0 = min(w.bbox.x0 for w in matched_words)
        min_y0 = min(w.bbox.y0 for w in matched_words)
        max_x1 = max(w.bbox.x1 for w in matched_words)
        max_y1 = max(w.bbox.y1 for w in matched_words)

        return {
            "page": first_word.bbox.page,
            "x0": min_x0,
            "y0": min_y0,
            "x1": max_x1,
            "y1": max_y1,
        }

    def close(self) -> None:
        """Release resources."""
        logger.info("NLPService resources released")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
