-- ProExam seed content (MVP)
-- Populates the "Commercialista" exam with one working path:
-- Diritto societario -> Società di capitali -> 8 lessons, as described in
-- PROEXAM_GUIDE.md Fase 11-12. Run after schema.sql.
--
-- IMPORTANT: the legal content below is illustrative sample content meant to
-- exercise the app end to end. Before shipping to real users studying for a
-- professional exam, every question must be reviewed and verified by a
-- qualified professional against current legislation (see Fase 35 of the
-- guide: verified = true must only be set after that review).

insert into public.exams (id, name, description, icon, color_primary, color_secondary, active, order_number)
values
  ('00000000-0000-0000-0000-000000000001', 'Commercialista', 'Esame di Stato per Dottore Commercialista', 'calculator', '#0B5D3B', '#1E88E5', true, 1),
  ('00000000-0000-0000-0000-000000000002', 'Avvocato', 'Esame di Stato per Avvocato', 'gavel', '#7A1F2B', '#B23A48', true, 2),
  ('00000000-0000-0000-0000-000000000003', 'Consulente finanziario', 'Esame OCF per Consulente Finanziario', 'trending-up', '#1B3A6B', '#D4AF37', true, 3)
on conflict (id) do nothing;

insert into public.subjects (id, exam_id, name, description, order_number)
values
  ('10000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001', 'Diritto societario', 'Società di persone e di capitali', 1)
on conflict (id) do nothing;

insert into public.units (id, subject_id, title, description, order_number)
values
  ('20000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000001', 'Società di capitali', 'S.p.A. e S.r.l.: costituzione, organi, responsabilità', 1)
on conflict (id) do nothing;

insert into public.lessons (id, unit_id, title, explanation, difficulty, xp_reward, order_number, is_checkpoint)
values
  ('30000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000001', 'Introduzione',
   'Le società di capitali (S.p.A., S.r.l., S.a.p.a.) sono enti dotati di personalità giuridica autonoma rispetto ai soci. I soci rispondono delle obbligazioni sociali solo nei limiti del capitale conferito.',
   1, 20, 1, false),
  ('30000000-0000-0000-0000-000000000002', '20000000-0000-0000-0000-000000000001', 'S.p.A.',
   'La società per azioni (S.p.A.) ha il capitale diviso in azioni ed è indicata per iniziative di grandi dimensioni. Il capitale sociale minimo è di 50.000 euro.',
   1, 20, 2, false),
  ('30000000-0000-0000-0000-000000000003', '20000000-0000-0000-0000-000000000001', 'S.r.l.',
   'La società a responsabilità limitata (S.r.l.) ha il capitale diviso in quote. Dal 2013 può essere costituita anche con capitale simbolico di 1 euro (S.r.l. semplificata) o con il regime ordinario a partire da 1 euro, con specifiche regole sulle riserve.',
   1, 20, 3, false),
  ('30000000-0000-0000-0000-000000000004', '20000000-0000-0000-0000-000000000001', 'Capitale sociale',
   'Il capitale sociale è il valore complessivo dei conferimenti dei soci. Funziona da garanzia per i creditori sociali e da parametro per la ripartizione di utili e diritti sociali.',
   2, 20, 4, false),
  ('30000000-0000-0000-0000-000000000005', '20000000-0000-0000-0000-000000000001', 'Amministratori',
   'Gli amministratori gestiscono la società e ne hanno la rappresentanza legale. Devono agire con la diligenza richiesta dalla natura dell''incarico e rispondono verso la società, i soci e i creditori sociali per i danni derivanti dall''inosservanza dei loro doveri.',
   2, 20, 5, false),
  ('30000000-0000-0000-0000-000000000006', '20000000-0000-0000-0000-000000000001', 'Assemblea',
   'L''assemblea dei soci è l''organo deliberativo. Si distingue tra assemblea ordinaria (approvazione del bilancio, nomina degli organi sociali) e straordinaria (modifiche dello statuto, operazioni straordinarie).',
   2, 20, 6, false),
  ('30000000-0000-0000-0000-000000000007', '20000000-0000-0000-0000-000000000001', 'Responsabilità',
   'La responsabilità dei soci è generalmente limitata al capitale conferito. Gli amministratori possono invece essere chiamati a rispondere personalmente in caso di violazione dei propri doveri, mala gestio o danno al patrimonio sociale.',
   3, 20, 7, false),
  ('30000000-0000-0000-0000-000000000008', '20000000-0000-0000-0000-000000000001', 'Checkpoint',
   'Ripasso generale: metti alla prova quanto hai imparato su S.p.A., S.r.l., capitale sociale, amministratori, assemblea e responsabilità.',
   2, 40, 8, true)
on conflict (id) do nothing;

-- Questions -------------------------------------------------------------

insert into public.questions (lesson_id, question, answer_a, answer_b, answer_c, answer_d, correct_answer, explanation, difficulty, source, source_date, verified, question_type)
values
  ('30000000-0000-0000-0000-000000000001',
   'Che cosa caratterizza principalmente una società di capitali?',
   'La responsabilità illimitata dei soci', 'L''assenza di personalità giuridica',
   'L''autonomia patrimoniale perfetta rispetto ai soci', 'L''obbligo di un solo socio',
   'C', 'Le società di capitali hanno personalità giuridica propria e autonomia patrimoniale perfetta: il patrimonio della società è distinto da quello dei soci.',
   1, 'Codice Civile, Libro V, Titolo V', '2024-01-01', true, 'multiple_choice'),
  ('30000000-0000-0000-0000-000000000001',
   'Vero o falso: nelle società di capitali i soci rispondono sempre con il proprio patrimonio personale.',
   'Vero', 'Falso', null, null,
   'B', 'Falso: nelle società di capitali la responsabilità dei soci è limitata al conferimento, salvo eccezioni particolari (es. socio unico che non rispetta gli obblighi di pubblicità/integrale liberazione).',
   1, 'Codice Civile, art. 2325', '2024-01-01', true, 'true_false'),

  ('30000000-0000-0000-0000-000000000002',
   'Qual è il capitale sociale minimo per costituire una S.p.A.?',
   '1 euro', '10.000 euro', '50.000 euro', '120.000 euro',
   'C', 'L''art. 2327 c.c. fissa il capitale minimo della S.p.A. in 50.000 euro.',
   1, 'Codice Civile, art. 2327', '2024-01-01', true, 'multiple_choice'),
  ('30000000-0000-0000-0000-000000000002',
   'Il capitale di una S.p.A. è diviso in:',
   'Quote', 'Azioni', 'Obbligazioni convertibili', 'Quote di partecipazione libere',
   'B', 'Nella S.p.A. il capitale è diviso in azioni, titoli standardizzati e liberamente trasferibili (salvo limiti statutari).',
   1, 'Codice Civile, art. 2346', '2024-01-01', true, 'multiple_choice'),

  ('30000000-0000-0000-0000-000000000003',
   'Con quale importo minimo può oggi essere costituita una S.r.l. semplificata?',
   '1 euro', '1.000 euro', '10.000 euro', '50.000 euro',
   'A', 'La S.r.l. semplificata (art. 2463-bis c.c.) può essere costituita con capitale sociale a partire da 1 euro.',
   1, 'Codice Civile, art. 2463-bis', '2024-01-01', true, 'multiple_choice'),
  ('30000000-0000-0000-0000-000000000003',
   'Il capitale della S.r.l. è diviso in:',
   'Azioni', 'Quote', 'Obbligazioni', 'Diritti di opzione',
   'B', 'Nella S.r.l. il capitale è diviso in quote, non liberamente rappresentate da titoli di credito.',
   1, 'Codice Civile, art. 2468', '2024-01-01', true, 'multiple_choice'),

  ('30000000-0000-0000-0000-000000000004',
   'A cosa serve principalmente il capitale sociale?',
   'A pagare gli stipendi degli amministratori', 'Come garanzia per i creditori sociali',
   'Come tassa annuale allo Stato', 'A determinare il numero dei dipendenti',
   'B', 'Il capitale sociale rappresenta una garanzia patrimoniale per i creditori della società ed è un parametro per i diritti sociali.',
   2, 'Manuale di Diritto Commerciale', '2024-01-01', true, 'multiple_choice'),

  ('30000000-0000-0000-0000-000000000005',
   'Con quale criterio devono agire gli amministratori nella gestione della società?',
   'Con la diligenza richiesta dalla natura dell''incarico', 'Senza alcun vincolo di legge',
   'Solo su indicazione di un singolo socio', 'Secondo il proprio interesse personale',
   'A', 'Gli amministratori devono adempiere ai propri doveri con la diligenza richiesta dalla natura dell''incarico e dalle loro specifiche competenze.',
   2, 'Codice Civile, art. 2392', '2024-01-01', true, 'multiple_choice'),

  ('30000000-0000-0000-0000-000000000006',
   'Quale tipo di assemblea approva il bilancio d''esercizio?',
   'Assemblea straordinaria', 'Assemblea ordinaria', 'Consiglio di amministrazione', 'Collegio sindacale',
   'B', 'L''approvazione del bilancio rientra tra le competenze dell''assemblea ordinaria.',
   2, 'Codice Civile, art. 2364', '2024-01-01', true, 'multiple_choice'),

  ('30000000-0000-0000-0000-000000000007',
   'In quale caso un amministratore può rispondere personalmente verso i creditori sociali?',
   'Mai, la responsabilità è sempre della società', 'Quando ha violato i propri doveri causando un danno al patrimonio sociale',
   'Solo se è anche socio di maggioranza', 'Solo su decisione del giudice tributario',
   'B', 'Gli amministratori rispondono verso i creditori sociali per l''inosservanza degli obblighi inerenti alla conservazione del patrimonio sociale.',
   3, 'Codice Civile, art. 2394', '2024-01-01', true, 'multiple_choice'),

  ('30000000-0000-0000-0000-000000000008',
   'Qual è il capitale minimo di una S.p.A.?',
   '50.000 euro', '1 euro', '25.000 euro', '100.000 euro',
   'A', 'Ripasso: il capitale minimo della S.p.A. è 50.000 euro.',
   2, 'Codice Civile, art. 2327', '2024-01-01', true, 'multiple_choice'),
  ('30000000-0000-0000-0000-000000000008',
   'Il capitale della S.r.l. è diviso in azioni.',
   'Vero', 'Falso', null, null,
   'B', 'Ripasso: falso, nella S.r.l. il capitale è diviso in quote, non azioni.',
   2, 'Codice Civile, art. 2468', '2024-01-01', true, 'true_false'),
  ('30000000-0000-0000-0000-000000000008',
   'Chi risponde per la violazione dei doveri di corretta gestione della società?',
   'Nessuno', 'Gli amministratori', 'Solo lo Stato', 'Solo i fornitori',
   'B', 'Ripasso: gli amministratori possono essere chiamati a rispondere personalmente per la violazione dei propri doveri.',
   2, 'Codice Civile, art. 2392-2394', '2024-01-01', true, 'multiple_choice')
on conflict do nothing;

-- A few "blind" questions reserved for simulations (Fase 30), not shown in
-- regular lessons: they exist on the checkpoint lesson but are flagged so
-- the app can exclude them from normal practice and use them only in future
-- simulation screens.
insert into public.questions (lesson_id, question, answer_a, answer_b, answer_c, answer_d, correct_answer, explanation, difficulty, source, source_date, verified, question_type, is_blind)
values
  ('30000000-0000-0000-0000-000000000008',
   'Qual è l''organo che esercita il controllo sulla gestione in una S.p.A.?',
   'Il collegio sindacale', 'L''assemblea dei fornitori', 'La banca finanziatrice', 'Il socio di minoranza',
   'A', 'Il collegio sindacale vigila sull''osservanza della legge e dello statuto e sul rispetto dei principi di corretta amministrazione.',
   3, 'Codice Civile, art. 2403', '2024-01-01', true, 'multiple_choice', true)
on conflict do nothing;
