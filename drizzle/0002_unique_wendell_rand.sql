CREATE TABLE `donor_point_entries` (
	`id` text PRIMARY KEY NOT NULL,
	`donor_id` text NOT NULL,
	`amount` integer NOT NULL,
	`kind` text NOT NULL,
	`created_at` text NOT NULL,
	`applied` integer DEFAULT 0 NOT NULL
);
--> statement-breakpoint
ALTER TABLE `donors` ADD `points` integer DEFAULT 0 NOT NULL;--> statement-breakpoint
ALTER TABLE `reward_requests` ADD `donor_id` text;