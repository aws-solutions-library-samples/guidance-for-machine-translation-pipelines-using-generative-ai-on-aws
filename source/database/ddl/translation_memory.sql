-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE translation_memory (
    unique_id SERIAL PRIMARY KEY,
    source_text TEXT NOT NULL,
    target_text TEXT NOT NULL,
    source_text_embedding vector(1024), -- Add vector embedding column for source text
    target_text_embedding vector(1024), -- Add vector embedding column for target text
    source_lang VARCHAR(5) NOT NULL,
    target_lang VARCHAR(5) NOT NULL, 
    data_source VARCHAR(50) DEFAULT 'wmt19' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Add constraints to ensure valid language codes
    CONSTRAINT check_source_lang CHECK (source_lang ~ '^[a-z]{2}$'),
    CONSTRAINT check_target_lang CHECK (target_lang ~ '^[a-z]{2}$')
);

COMMENT ON COLUMN translation_memory.source_text IS 'Original text in source language';
COMMENT ON COLUMN translation_memory.target_text IS 'Translated text in target language';
COMMENT ON COLUMN translation_memory.source_lang IS 'Source language code (e.g., fr-FR)';
COMMENT ON COLUMN translation_memory.target_lang IS 'Target language code (e.g., de-DE)';
COMMENT ON COLUMN translation_memory.data_source IS 'Origin of the translation data';

-- Create indexes for commonly queried columns
CREATE INDEX idx_source_lang ON translation_memory(source_lang);
CREATE INDEX idx_target_lang ON translation_memory(target_lang);
CREATE INDEX idx_data_source ON translation_memory(data_source);

-- Add composite index for source_lang and data_source
CREATE INDEX idx_source_lang_data_source ON translation_memory(source_lang, data_source);

-- Create vector indexes
CREATE INDEX idx_source_text_embedding ON translation_memory USING ivfflat (source_text_embedding vector_cosine_ops);
CREATE INDEX idx_target_text_embedding ON translation_memory USING ivfflat (target_text_embedding vector_cosine_ops);

-- Add comment to table
COMMENT ON TABLE translations IS 'Stores translation pairs from WMT19 dataset and other sources';

-- Add comments to columns
COMMENT ON COLUMN translations.source_text_embedding IS 'Vector embedding of source text';
COMMENT ON COLUMN translations.target_text_embedding IS 'Vector embedding of target text';



COPY translations(source_text, target_text)
FROM PROGRAM 'sed 1d /path/to/wmt19_fr-de.csv'
WITH (
    FORMAT CSV,
    ENCODING 'UTF8'
);
