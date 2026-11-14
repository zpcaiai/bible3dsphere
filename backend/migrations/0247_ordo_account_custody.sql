-- An Ordo save can arrive after the erasure function has swept this table.
-- Deleting the parent account must also remove any such late committed row.
-- Reject pre-existing orphan rows without silently discarding their contents.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.ordo_amoris_records'::regclass
          AND conname = 'ordo_amoris_records_account_fk'
    ) THEN
        IF NOT EXISTS (
            SELECT 1
            FROM pg_constraint AS c
            JOIN pg_attribute AS source_key
              ON source_key.attrelid = c.conrelid AND source_key.attname = 'email'
            JOIN pg_attribute AS target_key
              ON target_key.attrelid = c.confrelid AND target_key.attname = 'email'
            WHERE c.conrelid = 'public.ordo_amoris_records'::regclass
              AND c.conname = 'ordo_amoris_records_account_fk'
              AND c.contype = 'f' AND c.confrelid = 'public.users'::regclass
              AND c.conkey = ARRAY[source_key.attnum]
              AND c.confkey = ARRAY[target_key.attnum]
              AND c.confupdtype = 'c' AND c.confdeltype = 'c' AND c.convalidated
        ) THEN
            RAISE EXCEPTION 'ordo_amoris_records_account_fk is an incompatible foreign key'
                USING ERRCODE = 'check_violation';
        END IF;
    ELSE
        ALTER TABLE public.ordo_amoris_records
            ADD CONSTRAINT ordo_amoris_records_account_fk
            FOREIGN KEY (email) REFERENCES public.users(email)
            ON UPDATE CASCADE ON DELETE CASCADE;
    END IF;
END
$$;
