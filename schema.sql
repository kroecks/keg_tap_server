-- Schema for Keg Tap management database

-- Drop tables if they exist
DROP TABLE IF EXISTS taps;
DROP TABLE IF EXISTS beers;

-- Create beers table
CREATE TABLE beers (
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       name TEXT NOT NULL,
                       abv REAL NOT NULL,
                       image_path TEXT
);

-- Create taps table
CREATE TABLE taps (
                      id INTEGER PRIMARY KEY AUTOINCREMENT,
                      tap_id TEXT UNIQUE NOT NULL,
                      beer_id INTEGER,
                      volume REAL NOT NULL DEFAULT 0,  -- in milliliters
                      flow_rate REAL NOT NULL DEFAULT 1.0,  -- in milliliters per second
                      FOREIGN KEY (beer_id) REFERENCES beers (id)
);

-- Insert some sample data
INSERT INTO beers (name, abv, image_path) VALUES
                                              ('IPA', 6.5, 'beer_images/default.jpg'),
                                              ('Stout', 5.0, 'beer_images/default.jpg'),
                                              ('Pilsner', 4.2, 'beer_images/default.jpg');

INSERT INTO taps (tap_id, beer_id, volume, flow_rate) VALUES
                                                          ('tap_1', 1, 5000, 15.0),  -- 5 liters of IPA, flowing at 15ml/sec
                                                          ('tap_2', 2, 5000, 12.0);  -- 5 liters of Stout, flowing at 12ml/sec
