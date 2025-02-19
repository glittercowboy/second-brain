UPDATE transcriptions 
SET categories = REPLACE(categories, 'work', 'Work')
WHERE categories LIKE '%work%';

UPDATE transcriptions 
SET categories = REPLACE(categories, 'purpose', 'Purpose')
WHERE categories LIKE '%purpose%';

UPDATE transcriptions 
SET categories = REPLACE(categories, 'health', 'Health')
WHERE categories LIKE '%health%';

UPDATE transcriptions 
SET categories = REPLACE(categories, 'relationships', 'Relationships')
WHERE categories LIKE '%relationships%';
