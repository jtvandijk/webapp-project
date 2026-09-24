-- Makes the column sname_clean_stand in census.gb1921: the surname cleaned in exactly the way of the old project (the
-- old function f_clean_surnames, written out as plain SQL). The pipeline reads this column for every census year.
--
-- This file is written for 1921. make_sname_clean_stand.sh (in this folder) runs it for every census year that lacks
-- the column, or for the years you name, by changing 1921 to that year. Use that rather than this file by hand:
--
--   bash tools/sql/make_sname_clean_stand.sh
--
-- By hand, for 1921:   psql <your connection> -1 -v ON_ERROR_STOP=1 -f census_sname_clean_stand.sql
-- -1 runs the whole file as ONE transaction: if anything goes wrong nothing is changed. It stops with an error, and
-- changes nothing, if the table already has the column. It prints two result tables (the biggest changes, and how
-- many people have an empty cleaned name): read them.
--
-- What it does: the cleaning works on a name, not on a person, so it is done once for each DIFFERENT name of the
-- year (census.sname_1921, about a million rows) and the result is then copied to the people in one pass. The
-- steps are those of the old function, with its step-12 line pointed at the right table.
-- Nothing else should use census.gb1921 while it runs (adding a column locks the table until the end), and no index
-- should be being built on it (adding a column waits for that to finish). Afterwards:  VACUUM ANALYZE census.gb1921;

DROP TABLE IF EXISTS census.sname_1921;
CREATE TABLE census.sname_1921 AS
	SELECT sname, COUNT(*) AS n FROM census.gb1921 GROUP BY sname;

ALTER TABLE census.sname_1921 ADD COLUMN sname_clean text;
ALTER TABLE census.sname_1921 ADD COLUMN sname_clean_ext text;
ALTER TABLE census.sname_1921 ADD COLUMN sname_clean_partial bool;
ALTER TABLE census.sname_1921 ADD COLUMN sname_clean_stand text;

-- [SPECIAL CHARACTERS]

-- 0) set: to lower case
UPDATE census.sname_1921
	SET sname_clean = LOWER(sname);

-- 1) remove: consecutive spaces
UPDATE census.sname_1921
	SET sname_clean = regexp_replace(sname_clean,'\s{2,}',' ','g');

-- 2) remove: (?)
UPDATE census.sname_1921
	SET sname_clean = regexp_replace(sname_clean,'(\(\?\))','');

-- 3) flag: partially captured names with . at end or at least two . in middle of name
UPDATE census.sname_1921
	SET sname_clean_partial = FALSE;
UPDATE census.sname_1921
	SET sname_clean = lower(regexp_replace(sname,'\.+.*','')),
			sname_clean_partial = TRUE
			WHERE sname_clean ~ '\.+$|[\w]+[\.]{2,}[\w]+';

-- 4) set: entries null where number of special characters >= number of normal characters - 1
UPDATE census.sname_1921
	SET sname_clean = NULL
	WHERE char_length(regexp_replace(sname_clean,'[\w]+','','g')) >=
				char_length(regexp_replace(sname_clean,'[^\w]+','','g'))-1;

-- 5) update: 0 to O to correct possible typos
UPDATE census.sname_1921
	SET sname_clean = regexp_replace(sname_clean,'0','o');

-- 6) remove: numeric values
UPDATE census.sname_1921
	SET sname_clean = regexp_replace(sname_clean,'[\d]','')
	WHERE sname_clean ~ '\d';

-- [PARENTHESES]

-- 7) remove: special case parentheses ) ... (
UPDATE census.sname_1921
	SET sname_clean = regexp_replace(substring(sname_clean FROM '\).*?\('),'[\s\)][\s\(]','','g')
	WHERE sname_clean ~ '\).*?\(';

-- 8) remove: parts in between parentheses (full parentheses), write part in between parentheses to secondary variable
UPDATE census.sname_1921
	SET sname_clean_ext = regexp_replace(substring(sname_clean FROM '\(.*?\)'),'[\(\)]','','g'),
			sname_clean = regexp_replace(sname_clean,'\(.*\)','')
	WHERE sname_clean ~ '\(.*?\)';

-- 9) remove: parts in between parentheses (only opening parenthesis), write part in between parentheses to secondary variable
UPDATE census.sname_1921
	SET sname_clean_ext = regexp_replace(substring(sname_clean FROM '\(.*'),'[\(]+',''),
			sname_clean = regexp_replace(sname_clean, '\(.*','')
	WHERE sname_clean ~ '\(.*';

-- 10) remove: parts in between parentheses (only closing parenthesis), write part in between parentheses to secondary variable
UPDATE census.sname_1921
	SET sname_clean_ext = regexp_replace(substring(sname_clean,'.*\)+\s{0,}?'),'\)+\s{0,}',''),
			sname_clean = regexp_replace(sname_clean,'.*\)+\s{0,}?','')
	WHERE sname_clean ~ '[\)]';

-- [OR]

-- 11) remove: parts after OR, write part after OR to secondary variable
UPDATE census.sname_1921
	SET sname_clean_ext = regexp_replace(substring(sname_clean FROM '[\s]or[\s].*'),'[\s]or[\s]',''),
			sname_clean = regexp_replace(sname_clean,'[\s]or[\s].*','')
	WHERE sname_clean ~ '[\s]or[\s]';

-- [INITIALS]

-- 12) replace: all . with space
UPDATE census.sname_1921
	SET sname_clean = regexp_replace(sname_clean,'\.',' ')
	WHERE sname_clean ~ '\.';
UPDATE census.sname_1921
	SET sname_clean = regexp_replace(sname_clean,'\s{2,}',' ','g');

-- 13) remove: initials (if more than one)
UPDATE census.sname_1921
	SET sname_clean = regexp_replace(sname_clean,'^(\w\s){2,}','')
	WHERE sname_clean ~ '^(\w\s){2,}';

-- 14) remove: initials (if not o,d)
UPDATE census.sname_1921
	SET sname_clean = regexp_replace(sname_clean,'^(\w\s){1}','')
	WHERE NOT sname_clean ~ '^(o\s){1,}|^(d\sa){1,}'
				AND sname_clean ~ '^(\w\s){1,}';

-- [FINALISE]

-- 15) remove: names with 1 letter | 2 letters with spaces in between | nk | empty strings
UPDATE census.sname_1921
	SET sname_clean = NULL
	WHERE (char_length(sname_clean) <= 1
	AND NOT sname_clean_partial = TRUE)
	OR (sname_clean ~ 'nk' AND char_length(sname_clean) <= 3)
	OR (sname_clean ~ '[\w{1}?][^\w{1,2}?][\w{1,2}?]' AND char_length(sname_clean) <= 3);

-- 16) remove: all remaining special characters (including trailing spaces), except for apostrophe and hyphen
UPDATE census.sname_1921
	SET sname_clean = regexp_replace(sname_clean,'^\s{1,}|\s{1,}$|[^\w^\s^\-^'']','');

-- 17) standardise: remove all special characters, write to separate variable
UPDATE census.sname_1921
	SET sname_clean_stand = regexp_replace(sname_clean,'[^\w]+','','g');

-- [LOOK] the biggest names that the cleaning changed (compared with just dropping everything that is not a letter)
SELECT sname, n AS people, sname_clean_stand
	FROM census.sname_1921
	WHERE sname_clean_stand IS DISTINCT FROM regexp_replace(lower(sname),'[^a-z]','','g')
	ORDER BY n DESC
	LIMIT 40;

-- [LOOK] how many people end up with no cleaned name at all (they will not be counted)
SELECT SUM(n) AS people,
	SUM(n) FILTER (WHERE sname_clean_stand IS NULL OR sname_clean_stand = '') AS people_with_no_cleaned_name
	FROM census.sname_1921;

-- [APPLY] copy the cleaned name to the people, in one pass
ALTER TABLE census.gb1921 ADD COLUMN sname_clean_stand text;
UPDATE census.gb1921 g
	SET sname_clean_stand = m.sname_clean_stand
	FROM census.sname_1921 m
	WHERE g.sname = m.sname;

-- [CHECK] every person that has a surname should now have a cleaned one, except the ones the cleaning emptied
SELECT COUNT(*) AS people, COUNT(sname) AS with_a_surname, COUNT(sname_clean_stand) AS with_a_cleaned_name
	FROM census.gb1921;
