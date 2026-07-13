import { createClient } from '@supabase/supabase-js';
import Parser from 'rss-parser';
import * as cheerio from 'cheerio';
import { generateObject } from 'ai';
import { anthropic } from '@ai-sdk/anthropic';
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
  case_ref: z.string().describe('A unique generated reference like PRJ-LIVE-DL-2024-0001 based on state code and year. MUST start with PRJ-LIVE-.'),
  victim_pseudonym: z.string().describe('A respectful pseudonym for the victim (e.g. VICTIM-DELHI-24). Never use real names.'),
  crime_category: CrimeCategory,
  status: CaseStatus,
  incident_date: z.string().optional().describe('YYYY-MM-DD format if known'),
  state: z.string().describe('Full state name, e.g., Maharashtra, Delhi, Uttar Pradesh'),
  headline: z.string().describe('One-line factual summary of the case suitable for public display. No victim names.'),
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
      model: anthropic('claude-haiku-4-5-20251001'),
      schema: ExtractionSchema,
      prompt: `Analyze the following news article and extract details about the legal case related to gender-based violence in India. If it's not a specific case (e.g., general statistics, opinion piece), set is_relevant to false.\n\nArticle Title: ${item.title}\n\nArticle Text:\n${content}`
    });

    if (!extracted.is_relevant) {
      console.log('Article is not relevant to a specific case.');
      return;
    }

    // The UI only shows cases whose case_ref starts with PRJ-LIVE-
    const caseRef = extracted.case_ref.startsWith('PRJ-LIVE-')
      ? extracted.case_ref
      : `PRJ-LIVE-${extracted.case_ref.replace(/^(IN|PRJ)-/, '')}`;

    console.log(`Extracted Case: ${caseRef}`);

    const { error: caseError } = await supabase
      .from('live_cases')
      .upsert({
        id: caseRef.toLowerCase(),
        case_ref: caseRef,
        crime_category: extracted.crime_category,
        status: extracted.status,
        incident_date: extracted.incident_date || null,
        state: extracted.state,
        district: extracted.district,
        pocso_applicable: extracted.pocso_applicable,
        conviction_achieved: extracted.status === 'CLOSED_CONVICTED',
        headline: extracted.headline,
        source_url: item.link,
        source_title: item.title,
      }, { onConflict: 'case_ref' });

    if (caseError) {
      console.error('Error inserting case:', caseError);
      return;
    }
    console.log('Successfully ingested case!');
  } catch (error) {
    console.error('Extraction failed:', error);
  }
}

const FEED_URLS = [
  'https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms',            // TOI India News
  'https://feeds.feedburner.com/ndtvnews-india-news',                        // NDTV India
  'https://www.thehindu.com/news/national/feeder/default.rss',               // The Hindu National
  'https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml',         // Hindustan Times India
  'https://indianexpress.com/section/india/feed/',                           // Indian Express India
];

const MAX_PER_RUN = 15; // across all feeds, for cost/rate limiting

async function runIngestion() {
  console.log('Starting automated ingestion run...');
  let processedCount = 0;

  for (const feedUrl of FEED_URLS) {
    if (processedCount >= MAX_PER_RUN) break;
    try {
      const feed = await parser.parseURL(feedUrl);
      console.log(`Fetched ${feed.items.length} items from ${feed.title}`);

      for (const item of feed.items) {
        if (processedCount >= MAX_PER_RUN) break;

        const textToSearch = (item.title + ' ' + (item.contentSnippet || '')).toLowerCase();
        const isMatch = KEYWORDS.some(kw => textToSearch.includes(kw));

        if (isMatch) {
          await processArticle(item);
          processedCount++;
        }
      }
    } catch (err) {
      console.error(`Failed to fetch RSS ${feedUrl}:`, err);
    }
  }
  console.log(`Ingestion run complete! Processed ${processedCount} articles.`);
}

runIngestion();
