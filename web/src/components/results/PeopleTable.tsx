import { motion } from 'framer-motion';
import { Users } from 'lucide-react';
import './PeopleTable.css';

interface Person {
  name?: string;
  date_of_birth?: string;
  id_number?: string;
  address?: string;
}

interface PeopleTableProps {
  people: Person[];
}

const containerVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.4,
      ease: [0.4, 0, 0.2, 1] as const,
      staggerChildren: 0.06,
    },
  },
};

const rowVariants = {
  hidden: { opacity: 0, x: -20 },
  visible: {
    opacity: 1,
    x: 0,
    transition: { duration: 0.3, ease: [0.4, 0, 0.2, 1] as const },
  },
};

function CellValue({ value }: { value: string | undefined }) {
  if (!value) {
    return <td className="people-table__td people-table__td--empty">—</td>;
  }
  return <td className="people-table__td">{value}</td>;
}

export function PeopleTable({ people }: PeopleTableProps) {
  if (people.length <= 1) {
    return null;
  }

  return (
    <motion.div
      className="people-table"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      role="region"
      aria-label="People identified in document"
    >
      <div className="people-table__header">
        <Users className="people-table__icon" size={20} aria-hidden="true" />
        <h3 className="people-table__title">People Identified</h3>
        <motion.span
          className="people-table__count"
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: 'spring', stiffness: 500, damping: 25, delay: 0.3 }}
        >
          {people.length}
        </motion.span>
      </div>

      <div className="people-table__scroll">
        <table className="people-table__table">
          <thead>
            <tr>
              <th className="people-table__th" scope="col">#</th>
              <th className="people-table__th" scope="col">Name</th>
              <th className="people-table__th" scope="col">Date of Birth</th>
              <th className="people-table__th" scope="col">ID Number</th>
              <th className="people-table__th" scope="col">Address</th>
            </tr>
          </thead>
          <tbody>
            {people.map((person, index) => (
              <motion.tr
                key={index}
                className="people-table__row"
                variants={rowVariants}
              >
                <td className="people-table__td people-table__td--index">{index + 1}</td>
                <CellValue value={person.name} />
                <CellValue value={person.date_of_birth} />
                <CellValue value={person.id_number} />
                <CellValue value={person.address} />
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>
    </motion.div>
  );
}
