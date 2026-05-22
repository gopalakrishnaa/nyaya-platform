import { createClient } from '@supabase/supabase-js';
import Parser from 'rss-parser';
import * as cheerio from 'cheerio';
import { generateObject } from 'ai';
import { createAnthropic } from '@ai-sdk/anthropic';
import { z } from 'zod';
import * as dotenv from 'dotenv';
import path from 'path';

// Load env
dotenv.config({ path: path.resolve(process.cwd(), '.env.local') });

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
if (!process.env.SUPABASE_SERVICE_ROLE_KEY) {
  console.warn('WARNING: SUPABASE_SERVICE_ROLE_KEY is not defined in .env.local. Falling back to NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY. Database writes might fail due to Row Level Security (RLS) policies.');
}
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!;
const supabase = createClient(supabaseUrl, supabaseServiceKey);

const anthropic = createAnthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
});

const parser = new Parser();

const KEYWORDS = ['rape', 'assault', 'pocso', 'murder', 'dowry', 'harassment', 'molestation', 'court'];

// Database schemas corresponding to ENUMs in schema.sql
const CrimeCategory = z.enum([
  'RAPE', 'GANG_RAPE', 'SEXUAL_ASSAULT', 'POCSO_VIOLATION', 'ACID_ATTACK',
  'DOMESTIC_VIOLENCE', 'DOWRY_DEATH', 'DOWRY_HARASSMENT', 'STALKING',
  'TRAFFICKING', 'MOLESTATION', 'EVE_TEASING', 'HONOR_KILLING',
  'FORCED_MARRIAGE', 'MARITAL_RAPE', 'CYBER_CRIME_AGAINST_WOMEN', 'OTHER'
]);

const CaseStatus = z.enum([
  'REPORTED', 'UNDER_INVESTIGATION', 'CHARGESHEET_FILED', 'CHARGES_FRAMED',
  'TRIAL_IN_PROGRESS', 'JUDGMENT_DELIVERED', 'APPEALED', 'CLOSED_CONVICTED',
  'CLOSED_ACQUITTED', 'CLOSED_COMPROMISED', 'CLOSED_NO_EVIDENCE', 'SUPPRESSED'
]);

const EventCategory = z.enum([
  'FIR_FILING', 'INVESTIGATION', 'MEDICAL', 'ARREST', 'BAIL',
  'CHARGESHEET', 'COURT_PROCEEDINGS', 'JUDGMENT', 'APPEAL', 'COMPENSATION',
  'ADMINISTRATIVE', 'MEDIA_COVERAGE'
]);

const EventType = z.enum([
  'FIR_REGISTERED', 'FIR_REJECTED', 'FIR_TRANSFERRED',
  'MEDICAL_EXAMINATION', 'MEDICAL_REPORT_FILED', 'FORENSIC_REPORT',
  'ARREST_MADE', 'ACCUSED_SURRENDERED', 'ACCUSED_ABSCONDING',
  'BAIL_GRANTED', 'BAIL_REJECTED', 'BAIL_CANCELLED',
  'CHARGESHEET_FILED', 'CHARGES_FRAMED', 'CHARGES_DISMISSED',
  'HEARING_SCHEDULED', 'HEARING_HELD', 'HEARING_ADJOURNED', 'WITNESS_EXAMINATION',
  'CONVICTION', 'ACQUITTAL', 'PARTIAL_CONVICTION',
  'APPEAL_FILED', 'APPEAL_ADMITTED', 'APPEAL_DISMISSED',
  'COMPENSATION_AWARDED', 'COMPENSATION_PAID',
  'TRANSFER_PETITION', 'JUDGE_RECUSAL', 'MEDIA_GAG_ORDER'
]);

const ExtractionSchema = z.object({
  is_relevant: z.boolean().describe('True if the article describes a specific real-world gender-based violence case in India.'),
  case_ref: z.string().describe('A unique generated reference like IN-DL-2024-001 based on state and year.'),
  victim_pseudonym: z.string().describe('A respectful pseudonym for the victim (e.g. VICTIM-DELHI-24). Never use real names.'),
  crime_category: CrimeCategory,
  status: CaseStatus,
  incident_date: z.string().optional().describe('YYYY-MM-DD format if known'),
  state: z.string().describe('2-letter state code, e.g., MH, DL, UP'),
  district: z.string().describe('City or district name'),
  court_name: z.string().optional(),
  pocso_applicable: z.boolean(),
  events: z.array(z.object({
    event_date: z.string().optional().describe('YYYY-MM-DD'),
    event_category: EventCategory,
    event_type: EventType,
    event_description: z.string().describe('1-2 sentence description of what happened')
  }))
});

async function extractArticleContent(url: string): Promise<string> {
  const res = await fetch(url);
  const html = await res.text();
  const $ = cheerio.load(html);
  
  // Clean up typical garbage
  $('script, style, nav, footer, header, aside, .ad, .advertisement').remove();
  
  const text = $('p').map((i, el) => $(el).text()).get().join('\n\n');
  return text.substring(0, 15000); // Limit to ~15k chars for LLM context
}

async function processArticle(item: any) {
  console.log(`Processing: ${item.title}`);
  
  const content = await extractArticleContent(item.link);
  if (content.length < 500) {
    console.log('Content too short, skipping.');
    return;
  }

  console.log('Extracting structured data using Claude...');
  try {
    const { object: extracted } = await generateObject({
      model: anthropic('claude-3-5-sonnet-20241022'),
      schema: ExtractionSchema,
      prompt: `Analyze the following news article and extract details about the legal case related to gender-based violence in India. If it's not a specific case (e.g., general statistics, opinion piece), set is_relevant to false.\n\nArticle Title: ${item.title}\n\nArticle Text:\n${content}`
    });

    if (!extracted.is_relevant) {
      console.log('Article is not relevant to a specific case.');
      return;
    }

    console.log(`Extracted Case: ${extracted.case_ref}`);

    // Insert into Supabase
    // 1. Insert Case
    const { data: caseData, error: caseError } = await supabase
      .from('cases')
      .upsert({
        case_ref: extracted.case_ref,
        victim_pseudonym: extracted.victim_pseudonym,
        crime_category: extracted.crime_category,
        status: extracted.status,
        incident_date: extracted.incident_date || null,
        state: extracted.state,
        district: extracted.district,
        court_name: extracted.court_name || null,
        pocso_applicable: extracted.pocso_applicable
      }, { onConflict: 'case_ref' })
      .select('id')
      .single();

    if (caseError) {
      console.error('Error inserting case:', caseError);
      return;
    }

    // 2. Insert Events
    if (extracted.events && extracted.events.length > 0) {
      const eventsToInsert = extracted.events.map(e => ({
        case_id: caseData.id,
        event_date: e.event_date || new Date().toISOString().split('T')[0],
        event_category: e.event_category,
        event_type: e.event_type,
        summary: e.event_description,
        source_attribution: [{ url: item.link }]
      }));

      const { error: eventError } = await supabase
        .from('case_events')
        .insert(eventsToInsert);

      if (eventError) {
        console.error('Error inserting events:', eventError);
      } else {
        console.log(`Successfully ingested case and ${eventsToInsert.length} events!`);
      }
    }
  } catch (error) {
    console.error('Extraction failed:', error);
  }
}

async function runIngestion() {
  console.log('Starting automated ingestion run...');
  const feedUrl = 'https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms'; // TOI India News
  
  try {
    const feed = await parser.parseURL(feedUrl);
    console.log(`Fetched ${feed.items.length} items from ${feed.title}`);

    let processedCount = 0;
    for (const item of feed.items) {
      if (processedCount >= 5) break; // Limit to 5 per run for cost/rate limiting

      const textToSearch = (item.title + ' ' + (item.contentSnippet || '')).toLowerCase();
      const isMatch = KEYWORDS.some(kw => textToSearch.includes(kw));

      if (isMatch) {
        await processArticle(item);
        processedCount++;
      }
    }
    console.log('Ingestion run complete!');
  } catch (err) {
    console.error('Failed to fetch RSS:', err);
  }
}

runIngestion();
