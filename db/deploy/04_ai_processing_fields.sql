-- AI Processing Fields Migration
-- Adds fields to clips table for storing AI processing results from ClipVault-AIProcessingWorker

-- Add OCR results fields
ALTER TABLE clips ADD COLUMN IF NOT EXISTS ocr_text TEXT;
ALTER TABLE clips ADD COLUMN IF NOT EXISTS ocr_regions_count INTEGER;

-- Add AI workflow results fields
ALTER TABLE clips ADD COLUMN IF NOT EXISTS ai_category TEXT;
ALTER TABLE clips ADD COLUMN IF NOT EXISTS ai_extracted_data JSONB DEFAULT '{}';
ALTER TABLE clips ADD COLUMN IF NOT EXISTS ai_confidence FLOAT CHECK (ai_confidence >= 0 AND ai_confidence <= 1);

-- Add universal actions results fields
ALTER TABLE clips ADD COLUMN IF NOT EXISTS universal_actions JSONB DEFAULT '[]';
ALTER TABLE clips ADD COLUMN IF NOT EXISTS contact_info JSONB DEFAULT '{}';
ALTER TABLE clips ADD COLUMN IF NOT EXISTS locations JSONB DEFAULT '[]';
ALTER TABLE clips ADD COLUMN IF NOT EXISTS platforms_found JSONB DEFAULT '{}';

-- Add processing metadata fields
ALTER TABLE clips ADD COLUMN IF NOT EXISTS processing_started_at TIMESTAMPTZ;
ALTER TABLE clips ADD COLUMN IF NOT EXISTS processing_completed_at TIMESTAMPTZ;
ALTER TABLE clips ADD COLUMN IF NOT EXISTS processing_duration_seconds FLOAT;
ALTER TABLE clips ADD COLUMN IF NOT EXISTS ai_model_used TEXT;
ALTER TABLE clips ADD COLUMN IF NOT EXISTS processing_cost DECIMAL(10,4);

-- Add AI-generated description field
ALTER TABLE clips ADD COLUMN IF NOT EXISTS ai_description TEXT;

-- Add indexes for AI category and confidence searches
CREATE INDEX IF NOT EXISTS idx_clips_ai_category ON clips(ai_category);
CREATE INDEX IF NOT EXISTS idx_clips_ai_confidence ON clips(ai_confidence);
CREATE INDEX IF NOT EXISTS idx_clips_processing_completed ON clips(processing_completed_at);

-- Add GIN indexes for JSONB fields for faster queries
CREATE INDEX IF NOT EXISTS idx_clips_ai_extracted_data ON clips USING GIN (ai_extracted_data);
CREATE INDEX IF NOT EXISTS idx_clips_universal_actions ON clips USING GIN (universal_actions);
CREATE INDEX IF NOT EXISTS idx_clips_contact_info ON clips USING GIN (contact_info);
CREATE INDEX IF NOT EXISTS idx_clips_platforms_found ON clips USING GIN (platforms_found);

-- Update the status enum to include AI processing states
-- Note: We need to check if constraint exists before dropping it
DO $$
BEGIN
    -- Check if the constraint exists and drop it
    IF EXISTS (SELECT 1 FROM information_schema.table_constraints 
               WHERE constraint_name = 'clips_status_check' 
               AND table_name = 'clips') THEN
        ALTER TABLE clips DROP CONSTRAINT clips_status_check;
    END IF;
    
    -- Add the new constraint with AI processing states
    ALTER TABLE clips ADD CONSTRAINT clips_status_check 
      CHECK (status IN ('pending', 'processing', 'ai_processing', 'completed', 'failed'));
END $$;

-- Add column comments for documentation
COMMENT ON COLUMN clips.ocr_text IS 'Text extracted from video frames using OCR';
COMMENT ON COLUMN clips.ocr_regions_count IS 'Number of text regions detected in frames';
COMMENT ON COLUMN clips.ai_category IS 'Content category determined by AI (restaurant_review, product, etc.)';
COMMENT ON COLUMN clips.ai_extracted_data IS 'Structured data extracted by AI workflow';
COMMENT ON COLUMN clips.ai_confidence IS 'Overall confidence score of AI processing (0.0-1.0)';
COMMENT ON COLUMN clips.universal_actions IS 'Array of actionable items discovered by Universal Action Agent';
COMMENT ON COLUMN clips.contact_info IS 'Contact information found (phones, emails, social media)';
COMMENT ON COLUMN clips.locations IS 'Physical locations and addresses discovered';
COMMENT ON COLUMN clips.platforms_found IS 'Platform-specific URLs and capabilities discovered';
COMMENT ON COLUMN clips.ai_description IS 'AI-generated engaging description of the content';
COMMENT ON COLUMN clips.processing_started_at IS 'When AI processing began';
COMMENT ON COLUMN clips.processing_completed_at IS 'When AI processing completed';
COMMENT ON COLUMN clips.processing_duration_seconds IS 'Total AI processing time in seconds';
COMMENT ON COLUMN clips.ai_model_used IS 'AI models used for processing (e.g., gpt-5, gpt-4o-transcribe)';
COMMENT ON COLUMN clips.processing_cost IS 'Cost of AI processing in USD';