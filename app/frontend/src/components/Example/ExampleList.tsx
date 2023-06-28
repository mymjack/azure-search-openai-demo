import { Example } from "./Example";

import styles from "./Example.module.css";

export type ExampleModel = {
    text: string;
    value: string;
};

const EXAMPLES: ExampleModel[] = [
    {
        text: "What benefits do you offer for students?",
        value: "What benefits do you offer for students?"
    },
    { text: "Does BMO have any first-time home buyer incentives?", value: "Does BMO have any first-time home buyer incentives?" },
    { text: "What travel credit cards can I get?", value: "What travel credit cards can I get?" }
];

interface Props {
    onExampleClicked: (value: string) => void;
}

export const ExampleList = ({ onExampleClicked }: Props) => {
    return (
        <ul className={styles.examplesNavList}>
            {EXAMPLES.map((x, i) => (
                <li key={i}>
                    <Example text={x.text} value={x.value} onClick={onExampleClicked} />
                </li>
            ))}
        </ul>
    );
};
